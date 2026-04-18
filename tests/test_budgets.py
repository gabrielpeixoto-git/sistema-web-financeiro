from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.budgets.service import (
    delete_budget,
    list_rows,
    spent_in_category_month,
    upsert_budget,
)
from financas_app.app.modules.categories.service import create_category
from financas_app.app.modules.transactions.service import create_transaction


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bud_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str, name: str) -> User:
    u = User(email=email, name=name, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_spent_only_out_in_month(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "b1@test.com", "U")
        a = create_account(s, user_id=u.id, currency="BRL", name="C")
        cat = create_category(s, user_id=u.id, name="Food")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="out",
            amount="50,00",
            occurred_on=date(2026, 4, 10),
            category_id=cat.id,
        )
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="100,00",
            occurred_on=date(2026, 4, 10),
            category_id=cat.id,
        )
        assert spent_in_category_month(s, user_id=u.id, category_id=cat.id, year=2026, month=4) == 5000


def test_budget_row_and_upsert_update(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "b2@test.com", "U")
        create_account(s, user_id=u.id, currency="BRL", name="A")
        cat = create_category(s, user_id=u.id, name="X")
        b1 = upsert_budget(
            s, user_id=u.id, category_id=cat.id, year=2026, month=5, amount="200,00"
        )
        b2 = upsert_budget(
            s, user_id=u.id, category_id=cat.id, year=2026, month=5, amount="300,00"
        )
        assert b1.id == b2.id
        assert b2.limit_cents == 30000
        rows = list_rows(s, user_id=u.id, year=2026, month=5)
        assert len(rows) == 1
        assert rows[0].limit_cents == 30000


def test_delete_budget(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "b3@test.com", "U")
        create_account(s, user_id=u.id, currency="BRL", name="A")
        cat = create_category(s, user_id=u.id, name="Y")
        b = upsert_budget(s, user_id=u.id, category_id=cat.id, year=2026, month=6, amount="10,00")
        delete_budget(s, user_id=u.id, budget_id=b.id)
        assert list_rows(s, user_id=u.id, year=2026, month=6) == []
