from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
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


def init_db() -> None:
    """Create all tables. Import models so they register with Base.metadata."""
    from app.models import exit_request, schedule, template, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


# Lightweight, additive migrations for columns added after a DB already exists.
# (No Alembic in this project; create_all never alters existing tables.)
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
