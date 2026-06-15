from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.scheduler import register_schedule, remove_schedule
from app.db.database import get_db
from app.models.schedule import Schedule
from app.models.template import Template
from app.models.user import User
from app.schemas.exit_request import ExitRequestOut
from app.schemas.schedule import (
    ScheduleBulkRunRequest,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
)
from app.services.submission import (
    SubmissionError,
    apply_date_strategy,
    execute_pending_submission,
    resolve_payload,
    start_submission,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _get_owned(db: Session, user: User, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None or schedule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


def _validate_template(db: Session, user: User, template_id: int | None) -> None:
    if template_id is None:
        return
    template = db.get(Template, template_id)
    if template is None or template.user_id != user.id:
        raise HTTPException(status_code=400, detail="Template not found")


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Schedule).where(Schedule.user_id == user.id).order_by(Schedule.id.desc())
    ).all()


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_template(db, user, data.template_id)
    schedule = Schedule(
        user_id=user.id,
        name=data.name,
        template_id=data.template_id,
        payload=data.payload,
        trigger_type=data.trigger_type,
        run_at=data.run_at,
        hour=data.hour,
        minute=data.minute,
        cron=data.cron,
        date_strategy=data.date_strategy,
        enabled=data.enabled,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    register_schedule(schedule)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned(db, user, schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    schedule = _get_owned(db, user, schedule_id)
    if data.template_id is not None:
        _validate_template(db, user, data.template_id)

    for field in (
        "name",
        "template_id",
        "payload",
        "trigger_type",
        "run_at",
        "hour",
        "minute",
        "cron",
        "date_strategy",
        "enabled",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    register_schedule(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    schedule = _get_owned(db, user, schedule_id)
    remove_schedule(schedule.id)
    db.delete(schedule)
    db.commit()


@router.post("/run-bulk", response_model=list[ExitRequestOut], status_code=status.HTTP_202_ACCEPTED)
def run_bulk(
    data: ScheduleBulkRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(data.schedule_ids) > settings.max_batch_items:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Máximo de {settings.max_batch_items} envios por vez "
                f"(selecionados: {len(data.schedule_ids)})."
            ),
        )

    results: list = []
    for schedule_id in data.schedule_ids:
        schedule = _get_owned(db, user, schedule_id)
        try:
            resolved = resolve_payload(db, user, schedule.template_id, schedule.payload)
            resolved = apply_date_strategy(resolved, schedule.date_strategy)
            record = start_submission(
                db,
                user,
                payload=resolved,
                schedule_id=schedule.id,
                source="schedule",
            )
            background_tasks.add_task(execute_pending_submission, record.id)
            results.append(record)
        except SubmissionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return results


@router.post(
    "/{schedule_id}/run-now",
    response_model=ExitRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_now(
    schedule_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    schedule = _get_owned(db, user, schedule_id)
    try:
        resolved = resolve_payload(db, user, schedule.template_id, schedule.payload)
        resolved = apply_date_strategy(resolved, schedule.date_strategy)
        record = start_submission(
            db,
            user,
            payload=resolved,
            schedule_id=schedule.id,
            source="schedule",
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    background_tasks.add_task(execute_pending_submission, record.id)
    return record
