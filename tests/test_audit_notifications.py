from sqlmodel import Session, SQLModel, create_engine, select

import financas_app.app.db.models  # noqa: F401
from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.audit.models import AuditLog
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.budgets.service import upsert_budget
from financas_app.app.modules.categories.service import create_category
from financas_app.app.modules.notifications.service import (
    create_notification,
    generate_for_user,
    list_notifications,
)
from financas_app.app.modules.transactions.service import create_transaction


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit_notify_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session) -> User:
    u = User(email="audit@test.com", name="audit", hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_create_account_writes_audit_log(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        a = create_account(s, user_id=u.id, currency="BRL", name="Conta Audit")
        log = s.exec(
            select(AuditLog).where(
                AuditLog.user_id == u.id,
                AuditLog.action == "accounts.create",
                AuditLog.entity_id == a.id,
            )
        ).first()
        assert log is not None


def test_notifications_create_and_list(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        create_notification(s, user_id=u.id, kind="info", message="ola")
        generate_for_user(s, user_id=u.id)
        rows = list_notifications(s, user_id=u.id, limit=10)
        assert len(rows) == 2
        assert rows[0].message


def test_notifications_policies_budget_over_and_goal_overdue(tmp_path):
    from datetime import date, timedelta

    from financas_app.app.modules.goals.service import create_goal

    with _session(tmp_path) as s:
        u = _user(s)
        cat = create_category(s, user_id=u.id, name="Alimentação")
        acc = create_account(s, user_id=u.id, currency="BRL", name="Carteira")

        # budget in current month
        today = date.today()
        upsert_budget(s, user_id=u.id, category_id=cat.id, year=today.year, month=today.month, amount="10,00")
        create_transaction(
            s,
            user_id=u.id,
            account_id=acc.id,
            kind="out",
            amount="15,00",
            occurred_on=today,
            category_id=cat.id,
            description="mercado",
        )

        # overdue goal
        create_goal(s, user_id=u.id, name="Viagem", target="100,00", due_on=today - timedelta(days=1))

        generate_for_user(s, user_id=u.id)
        rows = list_notifications(s, user_id=u.id, limit=50)
        kinds = {n.kind for n in rows}
        assert "daily_summary" in kinds
        assert "budget_over" in kinds
        assert "goal_overdue" in kinds


def test_notifications_policy_budget_near_limit(tmp_path):
    from datetime import date

    with _session(tmp_path) as s:
        u = _user(s)
        cat = create_category(s, user_id=u.id, name="Transporte")
        acc = create_account(s, user_id=u.id, currency="BRL", name="Conta")
        today = date.today()
        upsert_budget(s, user_id=u.id, category_id=cat.id, year=today.year, month=today.month, amount="10,00")
        create_transaction(
            s,
            user_id=u.id,
            account_id=acc.id,
            kind="out",
            amount="9,00",
            occurred_on=today,
            category_id=cat.id,
            description="uber",
        )
        generate_for_user(s, user_id=u.id)
        kinds = {n.kind for n in list_notifications(s, user_id=u.id, limit=50)}
        assert "budget_near" in kinds
        assert "budget_over" not in kinds


def test_notifications_policy_goal_near_complete(tmp_path):
    from financas_app.app.modules.goals.service import add_progress, create_goal

    with _session(tmp_path) as s:
        u = _user(s)
        g = create_goal(s, user_id=u.id, name="Reserva", target="100,00", due_on=None)
        add_progress(s, user_id=u.id, goal_id=g.id, amount="85,00")
        generate_for_user(s, user_id=u.id)
        kinds = {n.kind for n in list_notifications(s, user_id=u.id, limit=50)}
        assert "goal_near" in kinds


def test_budget_near_skipped_when_threshold_above_spend_ratio(tmp_path):
    from datetime import date

    with _session(tmp_path) as s:
        u = _user(s)
        cat = create_category(s, user_id=u.id, name="Lazer")
        acc = create_account(s, user_id=u.id, currency="BRL", name="Conta")
        today = date.today()
        upsert_budget(s, user_id=u.id, category_id=cat.id, year=today.year, month=today.month, amount="10,00")
        create_transaction(
            s,
            user_id=u.id,
            account_id=acc.id,
            kind="out",
            amount="9,00",
            occurred_on=today,
            category_id=cat.id,
            description="x",
        )
        generate_for_user(s, user_id=u.id, budget_near_pct=95)
        kinds = {n.kind for n in list_notifications(s, user_id=u.id, limit=50)}
        assert "budget_near" not in kinds


def test_goal_near_skipped_when_threshold_above_progress_ratio(tmp_path):
    from financas_app.app.modules.goals.service import add_progress, create_goal

    with _session(tmp_path) as s:
        u = _user(s)
        g = create_goal(s, user_id=u.id, name="Carro", target="100,00", due_on=None)
        add_progress(s, user_id=u.id, goal_id=g.id, amount="85,00")
        generate_for_user(s, user_id=u.id, goal_near_pct=90)
        kinds = {n.kind for n in list_notifications(s, user_id=u.id, limit=50)}
        assert "goal_near" not in kinds

