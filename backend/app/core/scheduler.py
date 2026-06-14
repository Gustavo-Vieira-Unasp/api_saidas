"""APScheduler integration.

Jobs are persisted in a SQLAlchemy job store so they survive restarts. Each
`Schedule` row maps to one APScheduler job whose id is `schedule_<id>`.

The job callable is module-level (`run_scheduled_submission`) so it can be
serialized by the persistent job store.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {"default": SQLAlchemyJobStore(url=settings.database_url)}
        _scheduler = BackgroundScheduler(
            jobstores=jobstores, timezone=settings.scheduler_timezone
        )
    return _scheduler


def hydrate_schedules() -> None:
    """Re-register all enabled schedules from the DB into APScheduler."""
    from app.db.database import SessionLocal
    from app.models.schedule import Schedule

    db = SessionLocal()
    try:
        schedules = db.scalars(
            select(Schedule).where(Schedule.enabled.is_(True))
        ).all()
        for schedule in schedules:
            register_schedule(schedule)
        logger.info("Hydrated %d enabled schedule(s) into APScheduler", len(schedules))
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        hydrate_schedules()


def shutdown_scheduler() -> None:
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)


def _build_trigger(schedule) -> CronTrigger | DateTrigger:
    """Translate a Schedule row into an APScheduler trigger."""
    tz = settings.scheduler_timezone
    if schedule.trigger_type == "once":
        return DateTrigger(run_date=schedule.run_at, timezone=tz)
    if schedule.trigger_type == "daily":
        return CronTrigger(
            hour=schedule.hour, minute=schedule.minute or 0, timezone=tz
        )
    if schedule.trigger_type == "weekdays":
        return CronTrigger(
            day_of_week="mon-fri",
            hour=schedule.hour,
            minute=schedule.minute or 0,
            timezone=tz,
        )
    if schedule.trigger_type == "cron":
        return CronTrigger.from_crontab(schedule.cron, timezone=tz)
    raise ValueError(f"Unknown trigger_type: {schedule.trigger_type}")


def register_schedule(schedule) -> None:
    """Add or replace the APScheduler job for a Schedule. Removes it if disabled."""
    scheduler = get_scheduler()
    job_id = f"schedule_{schedule.id}"

    if not schedule.enabled:
        remove_schedule(schedule.id)
        return

    trigger = _build_trigger(schedule)
    scheduler.add_job(
        run_scheduled_submission,
        trigger=trigger,
        args=[schedule.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )


def remove_schedule(schedule_id: int) -> None:
    scheduler = get_scheduler()
    job_id = f"schedule_{schedule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def run_scheduled_submission(schedule_id: int) -> None:
    """Module-level job target. Loads the schedule and submits the exit."""
    from app.db.database import SessionLocal
    from app.models.schedule import Schedule
    from app.services.submission import (
        SubmissionError,
        apply_date_strategy,
        record_failed_submission,
        resolve_payload,
        run_submission,
    )

    db = SessionLocal()
    try:
        schedule = db.get(Schedule, schedule_id)
        if schedule is None or not schedule.enabled:
            return
        user = schedule.user
        try:
            resolved = resolve_payload(
                db, user, schedule.template_id, schedule.payload
            )
            resolved = apply_date_strategy(resolved, schedule.date_strategy)
            run_submission(
                db,
                user,
                payload=resolved,
                schedule_id=schedule.id,
                source="schedule",
            )
            schedule.last_run_at = datetime.now(UTC)
            db.commit()
        except SubmissionError as exc:
            logger.warning(
                "Scheduled submission failed for schedule_id=%s: %s",
                schedule_id,
                exc,
            )
            try:
                resolved = resolve_payload(
                    db, user, schedule.template_id, schedule.payload
                )
                resolved = apply_date_strategy(resolved, schedule.date_strategy)
            except SubmissionError:
                resolved = schedule.payload or {}
            record_failed_submission(
                db,
                user,
                payload=resolved,
                schedule_id=schedule.id,
                source="schedule",
                error=str(exc),
            )
    finally:
        db.close()
