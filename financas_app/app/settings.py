import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


def _load_dotenv_from_repo_root() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parent.parent.parent
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


class Settings(BaseModel):
    app_env: str = "dev"
    secret_key: str
    database_url: str = "sqlite:///./dev.db"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    password_reset_expire_minutes: int = 60
    app_timezone: str = "America/Sao_Paulo"
    rate_limit_window_seconds: int = 60
    rate_limit_auth_per_window: int = 20
    rate_limit_reset_per_window: int = 10
    rate_limit_import_per_window: int = 5
    rate_limit_refresh_per_window: int = 30
    notify_budget_near_percent: int = 80
    notify_goal_near_percent: int = 80
    notify_dedupe_hours: int = 24

    # Email SMTP settings for reminders
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    email_reminder_days_before: int = 3


def _int_clamped(raw: str | None, default: int, *, lo: int, hi: int) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        return default
    return max(lo, min(hi, v))


def required_env_vars(app_env: str) -> list[str]:
    required = ["APP_SECRET_KEY"]
    if app_env == "prod":
        required.append("DATABASE_URL")
    return required


def _rate_limit_defaults(app_env: str) -> dict[str, int]:
    if app_env == "prod":
        return {
            "window_seconds": 60,
            "auth_per_window": 20,
            "reset_per_window": 10,
            "import_per_window": 5,
            "refresh_per_window": 30,
        }
    return {
        "window_seconds": 60,
        "auth_per_window": 60,
        "reset_per_window": 30,
        "import_per_window": 15,
        "refresh_per_window": 90,
    }


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def validate_database_url(app_env: str, url: str) -> str:
    if app_env == "prod" and url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL in prod")
    return url


def validate_secret_key(app_env: str, secret_key: str) -> str:
    weak_values = {"change-me", "dev-secret", "test-secret", "secret", "123456", "password"}
    if app_env == "prod" and (len(secret_key) < 16 or secret_key.lower() in weak_values):
        raise RuntimeError("APP_SECRET_KEY is too weak for prod")
    return secret_key


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv_from_repo_root()
    app_env = os.getenv("APP_ENV", "dev")
    rate_limit = _rate_limit_defaults(app_env)
    raw_database_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    database_url = validate_database_url(app_env, normalize_database_url(raw_database_url))
    secret_key = validate_secret_key(app_env, os.getenv("APP_SECRET_KEY") or _req("APP_SECRET_KEY"))
    return Settings(
        app_env=app_env,
        secret_key=secret_key,
        database_url=database_url,
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")),
        password_reset_expire_minutes=int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "60")),
        app_timezone=os.getenv("APP_TIMEZONE", "America/Sao_Paulo"),
        rate_limit_window_seconds=int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS", str(rate_limit["window_seconds"]))
        ),
        rate_limit_auth_per_window=int(
            os.getenv("RATE_LIMIT_AUTH_PER_WINDOW", str(rate_limit["auth_per_window"]))
        ),
        rate_limit_reset_per_window=int(
            os.getenv("RATE_LIMIT_RESET_PER_WINDOW", str(rate_limit["reset_per_window"]))
        ),
        rate_limit_import_per_window=int(
            os.getenv("RATE_LIMIT_IMPORT_PER_WINDOW", str(rate_limit["import_per_window"]))
        ),
        rate_limit_refresh_per_window=int(
            os.getenv("RATE_LIMIT_REFRESH_PER_WINDOW", str(rate_limit["refresh_per_window"]))
        ),
        notify_budget_near_percent=_int_clamped(
            os.getenv("NOTIFICATION_BUDGET_NEAR_PERCENT"),
            80,
            lo=1,
            hi=99,
        ),
        notify_goal_near_percent=_int_clamped(
            os.getenv("NOTIFICATION_GOAL_NEAR_PERCENT"),
            80,
            lo=1,
            hi=99,
        ),
        notify_dedupe_hours=_int_clamped(os.getenv("NOTIFICATION_DEDUPE_HOURS"), 24, lo=1, hi=168),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
        smtp_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
        email_reminder_days_before=_int_clamped(os.getenv("EMAIL_REMINDER_DAYS"), 3, lo=1, hi=14),
    )