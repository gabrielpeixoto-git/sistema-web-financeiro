from fastapi.testclient import TestClient

from financas_app.app.settings import get_settings


def test_startup_creates_tables_in_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    get_settings.cache_clear()

    calls = {"count": 0}

    def _fake_create_all(_engine):
        calls["count"] += 1

    from financas_app.app.main import create_app

    monkeypatch.setattr("financas_app.app.main.SQLModel.metadata.create_all", _fake_create_all)
    with TestClient(create_app()):
        pass
    assert calls["count"] == 1


def test_startup_does_not_create_tables_in_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("APP_SECRET_KEY", "super-strong-secret-key-123")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/app")
    get_settings.cache_clear()

    calls = {"count": 0, "connect": 0}

    def _fake_create_all(_engine):
        calls["count"] += 1

    class _Conn:
        def __enter__(self):
            calls["connect"] += 1
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    from financas_app.app.main import create_app

    monkeypatch.setattr("financas_app.app.main.SQLModel.metadata.create_all", _fake_create_all)
    monkeypatch.setattr("financas_app.app.main.get_engine", lambda: type("E", (), {"connect": lambda self: _Conn()})())
    with TestClient(create_app()):
        pass
    assert calls["count"] == 0
    assert calls["connect"] == 1
