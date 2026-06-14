from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Schedule(Base):
    """A recurring or one-off automated submission."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("templates.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))

    # trigger_type: one | daily | weekdays | cron
    trigger_type: Mapped[str] = mapped_column(String(32))
    run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # for "once"
    hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cron: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Inline payload used when no template is linked
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # How `data_saida` is resolved at run time for recurring jobs:
    # fixed (use the payload date) | today | tomorrow
    date_strategy: Mapped[str] = mapped_column(String(16), default="fixed")

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    user = relationship("User", back_populates="schedules")
    template = relationship("Template", back_populates="schedules")

    @property
    def job_id(self) -> str:
        return f"schedule_{self.id}"
