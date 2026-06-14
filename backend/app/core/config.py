import os
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Security
    secret_key: str = "change-me-jwt-secret"
    encryption_key: str = ""
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    # Database
    database_url: str = "sqlite:///./saidas.db"

    # Automation / target site
    pensionato_base_url: str = "https://pensionato.unasp.edu.br/"
    playwright_headless: bool = True
    screenshots_dir: str = "./screenshots"

    # Optional UNASP credentials for CLI tools (discover.py / run_once.py).
    # Loaded from .env so they stay out of the shell command line.
    unasp_ra: str = ""
    unasp_senha: str = ""

    # Scheduler
    scheduler_timezone: str = "America/Sao_Paulo"

    # Safety cap: max exits/schedules processed in a single batch or bulk-send.
    max_batch_items: int = 30

    # CORS — comma-separated for multiple origins (e.g. production + custom domain)
    frontend_origin: str = "http://localhost:5173"
    # Optional regex for preview deploys (e.g. https://.*\.vercel\.app on Render)
    cors_origin_regex: str = ""

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.frontend_origin.split(",") if o.strip()]
        if "http://localhost:5173" not in origins:
            origins.append("http://localhost:5173")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


def bootstrap_production_secrets() -> None:
    """On Render, create/load secrets when env vars are missing.

    Render free tier has no persistent disk; secrets stored in env (Render
    dashboard) survive redeploys. File fallback survives restarts within the
    same container until the next redeploy.
    """
    if not os.getenv("RENDER"):
        return

    app_dir = Path.cwd()
    changed = False

    if not os.getenv("ENCRYPTION_KEY", "").strip():
        key_file = app_dir / ".encryption_key"
        if key_file.exists():
            os.environ["ENCRYPTION_KEY"] = key_file.read_text().strip()
        else:
            os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
            key_file.write_text(os.environ["ENCRYPTION_KEY"])
        changed = True

    if os.getenv("SECRET_KEY", "change-me-jwt-secret") == "change-me-jwt-secret":
        secret_file = app_dir / ".secret_key"
        if secret_file.exists():
            os.environ["SECRET_KEY"] = secret_file.read_text().strip()
        else:
            os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
            secret_file.write_text(os.environ["SECRET_KEY"])
        changed = True

    if changed:
        get_settings.cache_clear()


def validate_settings(settings: Settings | None = None) -> None:
    """Fail fast when required secrets are missing or insecure."""
    s = settings or get_settings()
    if not s.encryption_key.strip():
        hint = (
            "Set ENCRYPTION_KEY in Render Dashboard → Environment, or redeploy "
            "with RENDER=true so bootstrap can generate one."
            if os.getenv("RENDER")
            else (
                'Generate one with: python -c "from cryptography.fernet import '
                'Fernet; print(Fernet.generate_key().decode())"'
            )
        )
        raise RuntimeError(f"ENCRYPTION_KEY is required. {hint}")
    try:
        Fernet(s.encryption_key.encode())
    except Exception as exc:
        raise RuntimeError(
            "ENCRYPTION_KEY is not a valid Fernet key. "
            'Generate one with: python -c "from cryptography.fernet import '
            'Fernet; print(Fernet.generate_key().decode())"'
        ) from exc
    if s.secret_key == "change-me-jwt-secret":
        raise RuntimeError(
            "SECRET_KEY must be set to a unique value. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


bootstrap_production_secrets()
settings = get_settings()
