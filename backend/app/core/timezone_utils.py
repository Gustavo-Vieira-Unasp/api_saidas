"""America/Sao_Paulo helpers for schedules and display."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def scheduler_tz() -> ZoneInfo:
    return ZoneInfo(settings.scheduler_timezone)


def to_scheduler_naive(dt: datetime | None) -> datetime | None:
    """Wall-clock datetime in the scheduler timezone (naive, for DB + APScheduler).

    Naive values are assumed to already be in America/Sao_Paulo. Aware values
    (e.g. UTC from Postgres drivers) are converted first.
    """
    if dt is None:
        return None
    tz = scheduler_tz()
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(tz).replace(tzinfo=None)


def to_scheduler_iso(dt: datetime | None) -> str | None:
    """ISO-8601 with explicit Brasília offset for API responses."""
    if dt is None:
        return None
    naive = to_scheduler_naive(dt)
    return naive.replace(tzinfo=scheduler_tz()).isoformat()


def to_utc_iso(dt: datetime | None) -> str | None:
    """ISO-8601 UTC (Z suffix) for timestamps stored as UTC in the DB."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        aware = dt.replace(tzinfo=UTC)
    else:
        aware = dt.astimezone(UTC)
    return aware.isoformat().replace("+00:00", "Z")
