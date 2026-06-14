from functools import lru_cache

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


def validate_settings(settings: Settings | None = None) -> None:
    """Fail fast when required secrets are missing or insecure."""
    s = settings or get_settings()
    if not s.encryption_key.strip():
        raise RuntimeError(
            "ENCRYPTION_KEY is required. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    if s.secret_key == "change-me-jwt-secret":
        raise RuntimeError(
            "SECRET_KEY must be set to a unique value. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


settings = get_settings()
