from __future__ import annotations

from sqlmodel import Session, SQLModel

import financas_app.app.db.models  # noqa: F401
from financas_app.app.db.engine import get_engine
from financas_app.app.modules.auth.models import User
from financas_app.app.settings import get_settings


def test_run_for_all_users_processes_each_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cron_notify.db'}")
    get_settings.cache_clear()

    SQLModel.metadata.create_all(get_engine())
    with Session(get_engine()) as s:
        s.add(User(email="cron-script@test.com", name="c", hashed_password="x"))
        s.commit()

    from financas_app.scripts.generate_notifications import run_for_all_users

    n_users, n_created = run_for_all_users()
    assert n_users == 1
    assert n_created >= 1
