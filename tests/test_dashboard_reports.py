from datetime import date

import pytest
from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.dashboard.service import summary
from financas_app.app.modules.reports.service import period_report
from financas_app.app.modules.transactions.service import create_transaction


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dash_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str) -> User:
    u = User(email=email, name=email.split("@")[0], hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_dashboard_summary_counts_and_totals(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "dash@test.com")
        a = create_account(s, user_id=u.id, currency="BRL", name="Carteira")

        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="in", amount="250,00", occurred_on=date(2026, 4, 1)
        )
        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="out", amount="100,00", occurred_on=date(2026, 4, 2)
        )

        d = summary(s, user_id=u.id)
        assert d.income_cents == 25000
        assert d.expense_cents == 10000
        assert d.balance_cents == 15000
        assert d.tx_count == 2


def test_report_period_filters_range(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "report@test.com")
        a = create_account(s, user_id=u.id, currency="BRL", name="Conta")

        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="in", amount="100,00", occurred_on=date(2026, 4, 1)
        )
        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="out", amount="20,00", occurred_on=date(2026, 4, 10)
        )
        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="out", amount="5,00", occurred_on=date(2026, 5, 1)
        )

        r = period_report(s, user_id=u.id, start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert r.income_cents == 10000
        assert r.expense_cents == 2000
        assert r.net_cents == 8000
        assert r.count == 2


def test_period_report_rejects_inverted_range(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "inv@test.com")
        with pytest.raises(ValueError):
            period_report(s, user_id=u.id, start=date(2026, 4, 10), end=date(2026, 4, 1))

