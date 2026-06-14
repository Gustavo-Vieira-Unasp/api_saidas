from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

TriggerType = Literal["once", "daily", "weekdays", "cron"]
DateStrategy = Literal["fixed", "today", "tomorrow"]


class ScheduleBase(BaseModel):
    name: str
    template_id: int | None = None
    payload: dict[str, Any] | None = None
    trigger_type: TriggerType
    run_at: datetime | None = None
    hour: int | None = None
    minute: int | None = None
    cron: str | None = None
    date_strategy: DateStrategy = "fixed"
    enabled: bool = True

    @model_validator(mode="after")
    def _validate_trigger(self) -> "ScheduleBase":
        if self.trigger_type == "once" and self.run_at is None:
            raise ValueError("run_at is required for trigger_type 'once'")
        if self.trigger_type in ("daily", "weekdays") and self.hour is None:
            raise ValueError("hour is required for daily/weekdays triggers")
        if self.trigger_type == "cron" and not self.cron:
            raise ValueError("cron expression is required for trigger_type 'cron'")
        if self.template_id is None and not self.payload:
            raise ValueError("Provide either template_id or payload")
        return self


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: str | None = None
    template_id: int | None = None
    payload: dict[str, Any] | None = None
    trigger_type: TriggerType | None = None
    run_at: datetime | None = None
    hour: int | None = None
    minute: int | None = None
    cron: str | None = None
    date_strategy: DateStrategy | None = None
    enabled: bool | None = None


class ScheduleBulkRunRequest(BaseModel):
    schedule_ids: list[int]

    @model_validator(mode="after")
    def _non_empty(self) -> "ScheduleBulkRunRequest":
        if not self.schedule_ids:
            raise ValueError("Provide at least one schedule_id")
        return self


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template_id: int | None
    payload: dict[str, Any] | None
    trigger_type: str
    run_at: datetime | None
    hour: int | None
    minute: int | None
    cron: str | None
    date_strategy: str
    enabled: bool
    last_run_at: datetime | None
    created_at: datetime
