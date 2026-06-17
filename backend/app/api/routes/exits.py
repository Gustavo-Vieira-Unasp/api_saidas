from datetime import datetime, time, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.scheduler import register_schedule
from app.db.database import get_db
from app.models.exit_request import ExitRequest
from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.exit_request import (
    ExitBatchFailure,
    ExitBatchRequest,
    ExitBatchResult,
    ExitRequestOut,
    ExitSendRequest,
)
from app.services.submission import (
    SubmissionError,
    apply_weekly_times_for_date,
    execute_pending_submission,
    record_failed_submission,
    resolve_payload,
    start_submission,
)

router = APIRouter(prefix="/exits", tags=["exits"])


def _parse_hhmm(value: str) -> time:
    hh, mm = (value.split(":") + ["00"])[:2]
    return time(int(hh), int(mm))


def _date_range(req: ExitBatchRequest) -> list:
    selected = set(req.weekdays) if req.weekdays is not None else None
    days = []
    current = req.start_date
    while current <= req.end_date:
        if selected is not None:
            include = current.weekday() in selected
        else:
            include = not req.weekdays_only or current.weekday() < 5
        if include:
            days.append(current)
        current += timedelta(days=1)
    return days


@router.post("/send", response_model=ExitRequestOut, status_code=status.HTTP_202_ACCEPTED)
async def send_exit(
    data: ExitSendRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        record = start_submission(
            db,
            user,
            template_id=data.template_id,
            payload=data.payload,
            source="manual",
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    background_tasks.add_task(
        execute_pending_submission, record.id, dry_run=data.dry_run
    )
    return record


@router.post("/batch", response_model=ExitBatchResult)
async def batch_exit(
    data: ExitBatchRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        base = resolve_payload(db, user, data.template_id, data.payload)
    except SubmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    days = _date_range(data)
    if not days:
        raise HTTPException(status_code=400, detail="No dates in the selected range")
    if len(days) > settings.max_batch_items:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Máximo de {settings.max_batch_items} saídas por operação "
                f"(selecionados: {len(days)}). Reduza o intervalo ou os dias da semana."
            ),
        )

    base = dict(base)
    weekly_times = base.pop("weekly_times", None)

    result = ExitBatchResult()
    schedule_time = _parse_hhmm(data.schedule_at) if data.schedule_at else None

    for day in days:
        if weekly_times:
            payload = apply_weekly_times_for_date(
                {**base, "data_saida": day.isoformat(), "weekly_times": weekly_times},
                day,
            )
        else:
            payload = {**base, "data_saida": day.isoformat()}
            if data.hora_saida:
                payload["hora_saida"] = data.hora_saida
            if data.hora_retorno:
                payload["hora_retorno"] = data.hora_retorno

        if schedule_time is not None:
            schedule = Schedule(
                user_id=user.id,
                name=f"Planejado {day.isoformat()}",
                template_id=None,
                payload=payload,
                trigger_type="once",
                run_at=datetime.combine(day, schedule_time),
                date_strategy="fixed",
                enabled=True,
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            register_schedule(schedule)
            result.scheduled.append(schedule)
        else:
            try:
                record = start_submission(
                    db,
                    user,
                    payload=payload,
                    source="batch",
                )
                background_tasks.add_task(
                    execute_pending_submission, record.id, dry_run=data.dry_run
                )
                result.sent.append(record)
            except SubmissionError as exc:
                record_failed_submission(
                    db,
                    user,
                    payload=payload,
                    source="batch",
                    error=str(exc),
                )
                result.failed.append(ExitBatchFailure(date=day, error=str(exc)))

    return result


@router.get("", response_model=list[ExitRequestOut])
def list_exits(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(ExitRequest).where(ExitRequest.user_id == user.id)
    if status_filter:
        query = query.where(ExitRequest.status == status_filter)
    query = query.order_by(ExitRequest.id.desc()).limit(limit)
    return db.scalars(query).all()


@router.get("/{exit_id}", response_model=ExitRequestOut)
def get_exit(
    exit_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(ExitRequest, exit_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Exit request not found")
    return record


@router.get("/{exit_id}/screenshot")
def get_exit_screenshot(
    exit_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(ExitRequest, exit_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Exit request not found")
    if not record.screenshot_path or not Path(record.screenshot_path).exists():
        raise HTTPException(status_code=404, detail="No screenshot available")
    return FileResponse(record.screenshot_path, media_type="image/png")
