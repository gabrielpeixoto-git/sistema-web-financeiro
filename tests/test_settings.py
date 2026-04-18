import pytest

from financas_app.app.settings import (
    get_settings,
    normalize_database_url,
    required_env_vars,
    validate_database_url,
    validate_secret_key,
)


def test_normalize_database_url_postgres_without_driver():
    url = "postgresql://user:pass@localhost:5432/app"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pass@localhost:5432/app"


def test_normalize_database_url_keeps_existing_driver():
    url = "postgresql+psycopg://user:pass@localhost:5432/app"
    assert normalize_database_url(url) == url


def test_normalize_database_url_keeps_sqlite():
    url = "sqlite:///./dev.db"
    assert normalize_database_url(url) == url


def test_rate_limit_defaults_for_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("APP_SECRET_KEY", "super-strong-secret-key-123")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/app")
    get_settings.cache_clear()
    s = get_settings()
    assert s.rate_limit_auth_per_window == 20
    assert s.rate_limit_reset_per_window == 10
    assert s.rate_limit_import_per_window == 5
    assert s.rate_limit_refresh_per_window == 30


def test_rate_limit_defaults_for_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    s = get_settings()
    assert s.rate_limit_auth_per_window == 60
    assert s.rate_limit_reset_per_window == 30
    assert s.rate_limit_import_per_window == 15
    assert s.rate_limit_refresh_per_window == 90


def test_notification_policy_env_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    s = get_settings()
    assert s.notify_budget_near_percent == 80
    assert s.notify_goal_near_percent == 80
    assert s.notify_dedupe_hours == 24


def test_notification_policy_env_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    monkeypatch.setenv("NOTIFICATION_BUDGET_NEAR_PERCENT", "90")
    monkeypatch.setenv("NOTIFICATION_GOAL_NEAR_PERCENT", "70")
    monkeypatch.setenv("NOTIFICATION_DEDUPE_HOURS", "48")
    get_settings.cache_clear()
    s = get_settings()
    assert s.notify_budget_near_percent == 90
    assert s.notify_goal_near_percent == 70
    assert s.notify_dedupe_hours == 48


def test_notification_policy_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    monkeypatch.setenv("NOTIFICATION_BUDGET_NEAR_PERCENT", "not-a-number")
    monkeypatch.setenv("NOTIFICATION_GOAL_NEAR_PERCENT", "200")
    monkeypatch.setenv("NOTIFICATION_DEDUPE_HOURS", "0")
    get_settings.cache_clear()
    s = get_settings()
    assert s.notify_budget_near_percent == 80
    assert s.notify_goal_near_percent == 99
    assert s.notify_dedupe_hours == 1


def test_rate_limit_env_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("APP_SECRET_KEY", "super-strong-secret-key-123")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/app")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_WINDOW", "99")
    get_settings.cache_clear()
    s = get_settings()
    assert s.rate_limit_auth_per_window == 99


def test_required_env_vars_for_dev():
    assert required_env_vars("dev") == ["APP_SECRET_KEY"]


def test_required_env_vars_for_prod():
    assert required_env_vars("prod") == ["APP_SECRET_KEY", "DATABASE_URL"]


def test_validate_database_url_rejects_sqlite_in_prod():
    with pytest.raises(RuntimeError):
        validate_database_url("prod", "sqlite:///./dev.db")


def test_validate_database_url_accepts_postgres_in_prod():
    url = "postgresql+psycopg://user:pass@localhost:5432/app"
    assert validate_database_url("prod", url) == url


def test_validate_secret_key_rejects_weak_value_in_prod():
    with pytest.raises(RuntimeError):
        validate_secret_key("prod", "change-me")


def test_validate_secret_key_rejects_short_value_in_prod():
    with pytest.raises(RuntimeError):
        validate_secret_key("prod", "short-secret")


def test_validate_secret_key_accepts_strong_value_in_prod():
    secret = "super-strong-secret-key-123"
    assert validate_secret_key("prod", secret) == secret
