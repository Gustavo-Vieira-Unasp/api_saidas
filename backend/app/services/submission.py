"""Orchestrates a single exit submission: resolve data, run automation, persist."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.automation.pensionato import Credentials, submit_exit
from app.core.config import settings
from app.core.security import decrypt_secret
from app.db.database import SessionLocal
from app.models.exit_request import ExitRequest
from app.models.schedule import Schedule
from app.models.template import Template
from app.models.user import User

logger = logging.getLogger(__name__)


class SubmissionError(Exception):
    pass


def resolve_payload(
    db: Session, user: User, template_id: int | None, payload: dict | None
) -> dict:
    """Return the form payload, pulling from the linked template when needed."""
    if payload:
        return payload
    if template_id is not None:
        template = db.get(Template, template_id)
        if template is None or template.user_id != user.id:
            raise SubmissionError("Template not found")
        return template.payload or {}
    raise SubmissionError("No payload or template provided")


def apply_date_strategy(payload: dict, strategy: str | None) -> dict:
    """Override `data_saida` with today/tomorrow when the schedule asks for it."""
    if strategy in (None, "", "fixed"):
        return payload
    today = datetime.now(ZoneInfo(settings.scheduler_timezone)).date()
    if strategy == "today":
        target = today
    elif strategy == "tomorrow":
        target = today + timedelta(days=1)
    else:
        return payload
    return {**payload, "data_saida": target.isoformat()}


def apply_weekly_times(payload: dict, when: datetime | None = None) -> dict:
    """Apply per-weekday hora_saida/hora_retorno from template weekly_times."""
    result = dict(payload)
    weekly_times = result.pop("weekly_times", None)
    if not weekly_times:
        return result

    tz = ZoneInfo(settings.scheduler_timezone)
    ref = when or datetime.now(tz)
    if ref.tzinfo is None:
        weekday = ref.date().weekday()
    else:
        weekday = ref.astimezone(tz).date().weekday()

    wt = weekly_times.get(str(weekday))
    if wt:
        if wt.get("hora_saida"):
            result["hora_saida"] = wt["hora_saida"]
        if wt.get("hora_retorno"):
            result["hora_retorno"] = wt["hora_retorno"]
    return result


def apply_weekly_times_for_date(payload: dict, day: date) -> dict:
    """Apply weekly_times for a specific calendar day (batch sends)."""
    return apply_weekly_times(
        payload,
        datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo(settings.scheduler_timezone)),
    )


def prepare_schedule_payload(db: Session, user: User, schedule: Schedule) -> dict:
    """Resolve template payload and apply date strategy + weekly times (America/Sao_Paulo)."""
    resolved = resolve_payload(db, user, schedule.template_id, schedule.payload)
    resolved = apply_date_strategy(resolved, schedule.date_strategy)
    return apply_weekly_times(resolved)


def _credentials(user: User) -> Credentials:
    if not user.has_unasp_credentials:
        raise SubmissionError(
            "Credenciais UNASP não encontradas. Atualize sua senha em "
            "Configurações ou cadastre-se novamente."
        )
    return Credentials(
        username=user.unasp_username or "",
        password=decrypt_secret(user.unasp_password_enc or ""),
        profile=user.unasp_profile,
    )


def record_failed_submission(
    db: Session,
    user: User,
    *,
    payload: dict,
    schedule_id: int | None = None,
    source: str = "schedule",
    error: str,
) -> ExitRequest:
    """Persist a failed submission attempt for visibility in History."""
    record = ExitRequest(
        user_id=user.id,
        schedule_id=schedule_id,
        payload=payload,
        status="failed",
        message=error,
        source=source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def start_submission(
    db: Session,
    user: User,
    *,
    template_id: int | None = None,
    payload: dict | None = None,
    schedule_id: int | None = None,
    source: str = "manual",
) -> ExitRequest:
    """Validate credentials and create a pending ExitRequest (no Playwright yet)."""
    resolved = resolve_payload(db, user, template_id, payload)
    _credentials(user)

    record = ExitRequest(
        user_id=user.id,
        schedule_id=schedule_id,
        payload=resolved,
        status="pending",
        source=source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


async def execute_pending_submission(exit_id: int, *, dry_run: bool = False) -> None:
    """Run Playwright for an existing pending ExitRequest (uses its own DB session)."""
    db = SessionLocal()
    record: ExitRequest | None = None
    try:
        record = db.get(ExitRequest, exit_id)
        if record is None or record.status != "pending":
            return

        user = record.user
        creds = _credentials(user)
        result = await submit_exit(creds, record.payload, dry_run=dry_run)

        record.status = result.status
        record.message = result.message
        record.screenshot_path = result.screenshot_path
        db.commit()
    except SubmissionError as exc:
        logger.warning("Submission %s failed: %s", exit_id, exc)
        if record is not None:
            record.status = "failed"
            record.message = str(exc)
            db.commit()
    except Exception as exc:
        logger.exception("Submission %s failed unexpectedly", exit_id)
        if record is not None:
            record.status = "failed"
            record.message = str(exc)
            db.commit()
    finally:
        db.close()


async def run_submission_async(
    db: Session,
    user: User,
    *,
    template_id: int | None = None,
    payload: dict | None = None,
    schedule_id: int | None = None,
    source: str = "manual",
    dry_run: bool = False,
) -> ExitRequest:
    """Run submission inline (used by scheduler and tests)."""
    record = start_submission(
        db,
        user,
        template_id=template_id,
        payload=payload,
        schedule_id=schedule_id,
        source=source,
    )
    await execute_pending_submission(record.id, dry_run=dry_run)
    db.refresh(record)
    return record


def run_submission(
    db: Session,
    user: User,
    *,
    template_id: int | None = None,
    payload: dict | None = None,
    schedule_id: int | None = None,
    source: str = "manual",
    dry_run: bool = False,
) -> ExitRequest:
    """Synchronous entry point; runs Playwright on the FastAPI event loop when available."""
    from app.core.submission_runner import run_async

    async def _run() -> ExitRequest:
        return await run_submission_async(
            db,
            user,
            template_id=template_id,
            payload=payload,
            schedule_id=schedule_id,
            source=source,
            dry_run=dry_run,
        )

    return run_async(_run())
