"""Gera notificações para todos os usuários (cron). Uso: ``python -m financas_app.scripts.generate_notifications``. Ver PROD_RUNBOOK.md."""

from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.db import models as _models  # noqa: F401
from financas_app.app.db.engine import get_engine
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.notifications import service
from financas_app.app.settings import get_settings


def run_for_all_users() -> tuple[int, int]:
    st = get_settings()
    created_total = 0
    with Session(get_engine()) as session:
        users = list(session.exec(select(User)).all())
        for u in users:
            created_total += service.generate_for_user(
                session,
                user_id=u.id,
                budget_near_pct=st.notify_budget_near_percent,
                goal_near_pct=st.notify_goal_near_percent,
                dedupe_hours=st.notify_dedupe_hours,
            )
    return (len(users), created_total)


def main() -> None:
    n_users, n_created = run_for_all_users()
    print(f"users={n_users} notifications_created={n_created}")


if __name__ == "__main__":
    main()
