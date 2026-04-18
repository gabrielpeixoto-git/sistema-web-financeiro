from datetime import date

from sqlmodel import SQLModel, Session, create_engine, select

from financas_app.app.common.dates import add_one_month, advance_by_frequency
from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.recurring.models import RecurringRule
from financas_app.app.modules.recurring.service import create_rule, materialize_due
from financas_app.app.modules.transactions.models import Transaction
from financas_app.app.modules.transactions.service import balance_for_account


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rec_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str, name: str) -> User:
    u = User(email=email, name=name, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_add_one_month_clamps_day():
    assert add_one_month(date(2026, 1, 31)) == date(2026, 2, 28)
    assert add_one_month(date(2026, 1, 15)) == date(2026, 2, 15)


def test_advance_frequency():
    d = date(2026, 4, 1)
    assert advance_by_frequency(d, "daily") == date(2026, 4, 2)
    assert advance_by_frequency(d, "weekly") == date(2026, 4, 8)
    assert advance_by_frequency(d, "monthly") == date(2026, 5, 1)


def test_materialize_monthly_creates_and_advances(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "r1@test.com", "U")
        a = create_account(s, user_id=u.id, currency="BRL", name="C1")
        create_rule(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="out",
            amount="10,00",
            frequency="monthly",
            start_on=date(2026, 1, 10),
            end_on=None,
            description="Aluguel",
        )
        r = s.exec(select(RecurringRule).where(RecurringRule.user_id == u.id)).first()
        assert r is not None
        assert r.next_due == date(2026, 1, 10)

        n = materialize_due(s, user_id=u.id, until=date(2026, 3, 15))
        assert n == 3

        s.refresh(r)
        assert r.next_due == date(2026, 4, 10)

        txs = list(s.exec(select(Transaction).where(Transaction.user_id == u.id)).all())
        assert len(txs) == 3
        assert all(t.recurring_rule_id == r.id for t in txs)
        assert balance_for_account(s, user_id=u.id, account_id=a.id) == -3000


def test_materialize_idempotent(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "r2@test.com", "U")
        a = create_account(s, user_id=u.id, currency="BRL", name="C1")
        create_rule(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="5,00",
            frequency="weekly",
            start_on=date(2026, 4, 1),
            description="x",
        )
        materialize_due(s, user_id=u.id, until=date(2026, 4, 1))
        n2 = materialize_due(s, user_id=u.id, until=date(2026, 4, 1))
        assert n2 == 0
        count = len(list(s.exec(select(Transaction).where(Transaction.user_id == u.id)).all()))
        assert count == 1
