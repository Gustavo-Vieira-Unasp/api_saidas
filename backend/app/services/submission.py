"""Orchestrates a single exit submission: resolve data, run automation, persist."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.automation.pensionato import Credentials, submit_exit
from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.exit_request import ExitRequest
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
    """Async entry point for FastAPI routes. Runs automation without blocking the loop."""
    resolved = resolve_payload(db, user, template_id, payload)
    creds = _credentials(user)

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

    result = await submit_exit(creds, resolved, dry_run=dry_run)

    record.status = result.status
    record.message = result.message
    record.screenshot_path = result.screenshot_path
    db.commit()
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
    """Synchronous entry point for APScheduler jobs and CLI tools."""
    return asyncio.run(
        run_submission_async(
            db,
            user,
            template_id=template_id,
            payload=payload,
            schedule_id=schedule_id,
            source=source,
            dry_run=dry_run,
        )
    )
