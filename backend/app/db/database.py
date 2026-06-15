import logging
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_database_url(url: str) -> str:
    """Use psycopg3 driver when a bare postgresql:// URL is supplied."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres://")


def _create_engine(url: str):
    if _is_postgres(url):
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
    )


engine = _create_engine(_normalize_database_url(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """Apply Alembic migrations (Postgres production)."""
    from alembic import command
    from alembic.config import Config

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", _normalize_database_url(settings.database_url))
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied (head)")


def init_db() -> None:
    """Create or migrate tables. Import models so they register with Base.metadata."""
    from app.models import exit_request, schedule, template, user  # noqa: F401

    if _is_postgres(settings.database_url):
        run_migrations()
    else:
        Base.metadata.create_all(bind=engine)
        _ensure_columns()


# Lightweight, additive migrations for columns added after a DB already exists.
# SQLite-only; Postgres uses Alembic.
_ADDED_COLUMNS = {
    "schedules": {
        "date_strategy": "VARCHAR(16) DEFAULT 'fixed'",
    },
    # `ra` replaced `email` as the user identifier. SQLite cannot add a UNIQUE
    # column via ALTER, so legacy DBs are best recreated; this keeps the column
    # present as a fallback.
    "users": {
        "ra": "VARCHAR(64)",
    },
}


def _ensure_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
