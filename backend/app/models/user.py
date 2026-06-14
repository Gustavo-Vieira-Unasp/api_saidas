from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # RA (matrícula) is both the platform identifier and the UNASP username.
    ra: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # UNASP automation credentials (password stored encrypted). The username is
    # the RA, mirrored here so the automation layer keeps a single source.
    unasp_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unasp_password_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    unasp_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    templates = relationship(
        "Template", back_populates="user", cascade="all, delete-orphan"
    )
    schedules = relationship(
        "Schedule", back_populates="user", cascade="all, delete-orphan"
    )
    exit_requests = relationship(
        "ExitRequest", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_unasp_credentials(self) -> bool:
        return bool(self.unasp_username and self.unasp_password_enc)
