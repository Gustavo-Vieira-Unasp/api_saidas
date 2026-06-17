from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from app.core.timezone_utils import to_utc_iso
from app.schemas.schedule import ScheduleOut


class ExitSendRequest(BaseModel):
    """Send an exit immediately. Provide either template_id or inline payload."""

    template_id: int | None = None
    payload: dict[str, Any] | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _require_one(self) -> "ExitSendRequest":
        if self.template_id is None and not self.payload:
            raise ValueError("Provide either template_id or payload")
        return self


class ExitBatchRequest(BaseModel):
    """Plan several exits across a date range from one template/payload.

    For each date in [start_date, end_date] (optionally weekdays only) the base
    payload is copied with `data_saida` set to that date. When `schedule_at`
    (HH:MM) is given, a one-off schedule is created for each day; otherwise every
    day is submitted immediately.
    """

    template_id: int | None = None
    payload: dict[str, Any] | None = None
    start_date: date
    end_date: date
    weekdays_only: bool = False
    weekdays: list[int] | None = None
    hora_saida: str | None = None
    hora_retorno: str | None = None
    schedule_at: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate(self) -> "ExitBatchRequest":
        if self.template_id is None and not self.payload:
            raise ValueError("Provide either template_id or payload")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("Date range is limited to 366 days")
        if self.weekdays is not None and any(
            d < 0 or d > 6 for d in self.weekdays
        ):
            raise ValueError("weekdays must be between 0 (Mon) and 6 (Sun)")
        return self


class ExitRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int | None
    payload: dict[str, Any]
    status: str
    message: str | None
    source: str
    screenshot_path: str | None
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return to_utc_iso(value) or value.isoformat()


class ExitBatchFailure(BaseModel):
    date: date
    error: str


class ExitBatchResult(BaseModel):
    """Outcome of a batch plan: immediate submissions and/or created schedules."""

    sent: list[ExitRequestOut] = []
    scheduled: list[ScheduleOut] = []
    failed: list[ExitBatchFailure] = []
