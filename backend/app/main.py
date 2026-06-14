from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import auth, exits, meta, schedules, templates
from app.core.config import settings, validate_settings
from app.core.rate_limit import limiter
from app.core.scheduler import get_scheduler, shutdown_scheduler, start_scheduler
from app.db.database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="UNASP Exit Automation API",
    description="Automate exit authorization submissions to pensionato.unasp.edu.br",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(meta.router)
app.include_router(templates.router)
app.include_router(exits.router)
app.include_router(schedules.router)


@app.get("/", tags=["health"])
def health_root() -> dict:
    return {"status": "ok", "service": "unasp-exit-automation"}


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    scheduler = get_scheduler()
    job_count = len(scheduler.get_jobs()) if scheduler.running else 0

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "unasp-exit-automation",
        "database": "ok" if db_ok else "error",
        "scheduler_running": scheduler.running,
        "scheduled_jobs": job_count,
    }
