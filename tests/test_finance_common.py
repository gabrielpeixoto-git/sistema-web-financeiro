from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.common.finance import count_transactions, sum_by_kind
from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.transactions.service import create_transaction


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'finance_common.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session) -> User:
    u = User(email="common@test.com", name="common", hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_sum_by_kind_and_count_with_period(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        a = create_account(s, user_id=u.id, currency="BRL", name="Conta")
        create_transaction(s, user_id=u.id, account_id=a.id, kind="in", amount="100,00", occurred_on=date(2026, 4, 1))
        create_transaction(s, user_id=u.id, account_id=a.id, kind="out", amount="30,00", occurred_on=date(2026, 4, 10))
        create_transaction(s, user_id=u.id, account_id=a.id, kind="out", amount="5,00", occurred_on=date(2026, 5, 1))

        income = sum_by_kind(s, user_id=u.id, kind="in", start=date(2026, 4, 1), end=date(2026, 4, 30))
        expense = sum_by_kind(
            s, user_id=u.id, kind="out", start=date(2026, 4, 1), end=date(2026, 4, 30)
        )
        count = count_transactions(s, user_id=u.id, start=date(2026, 4, 1), end=date(2026, 4, 30))

        assert income == 10000
        assert expense == 3000
        assert count == 2
