import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from financas_app.app.settings import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_TIMEZONE", "UTC")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_WINDOW", "10000")
    monkeypatch.setenv("RATE_LIMIT_RESET_PER_WINDOW", "10000")
    monkeypatch.setenv("RATE_LIMIT_IMPORT_PER_WINDOW", "10000")
    monkeypatch.setenv("RATE_LIMIT_REFRESH_PER_WINDOW", "10000")
    get_settings.cache_clear()

    from financas_app.app.main import create_app

    from financas_app.app.db.engine import get_engine

    SQLModel.metadata.create_all(get_engine())
    app = create_app()
    return TestClient(app)