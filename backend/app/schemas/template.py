from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    name: str
    payload: dict[str, Any] = {}


class TemplateUpdate(BaseModel):
    name: str | None = None
    payload: dict[str, Any] | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    payload: dict[str, Any]
    created_at: datetime
