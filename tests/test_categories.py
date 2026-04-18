from datetime import date

import pytest
from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.categories.service import category_stats, create_category
from financas_app.app.modules.transactions.service import create_transaction


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cat_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str, name: str) -> User:
    u = User(email=email, name=name, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_category_stats_split_income_expense_and_net(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "cat@test.com", "Cat")
        a = create_account(s, currency="BRL", user_id=u.id, name="Conta")
        c = create_category(s, user_id=u.id, name="Mercado")
        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="in", amount="120,00", occurred_on=date(2026, 4, 1), category_id=c.id
        )
        create_transaction(
            s, user_id=u.id, account_id=a.id, kind="out", amount="50,00", occurred_on=date(2026, 4, 2), category_id=c.id
        )

        stats = category_stats(s, user_id=u.id, category_id=c.id)
        assert stats["category"].id == c.id
        assert stats["income_cents"] == 12000
        assert stats["expense_cents"] == 5000
        assert stats["net_cents"] == 7000
        assert stats["tx_count"] == 2


def test_category_stats_isolated_per_user(tmp_path):
    with _session(tmp_path) as s:
        u1 = _user(s, "u1@test.com", "U1")
        u2 = _user(s, "u2@test.com", "U2")
        a1 = create_account(s, currency="BRL", user_id=u1.id, name="A1")
        a2 = create_account(s, currency="BRL", user_id=u2.id, name="A2")
        c1 = create_category(s, user_id=u1.id, name="Transporte")
        c2 = create_category(s, user_id=u2.id, name="Transporte")
        create_transaction(
            s,
            user_id=u1.id,
            account_id=a1.id,
            kind="out",
            amount="30,00",
            occurred_on=date(2026, 4, 1),
            category_id=c1.id,
        )
        create_transaction(
            s,
            user_id=u2.id,
            account_id=a2.id,
            kind="out",
            amount="200,00",
            occurred_on=date(2026, 4, 1),
            category_id=c2.id,
        )

        stats = category_stats(s, user_id=u1.id, category_id=c1.id)
        assert stats["expense_cents"] == 3000
        assert stats["income_cents"] == 0
        assert stats["net_cents"] == -3000
        assert stats["tx_count"] == 1


def test_category_stats_filters_by_period(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "period@test.com", "Period")
        a = create_account(s, currency="BRL", user_id=u.id, name="Conta")
        c = create_category(s, user_id=u.id, name="Lazer")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="100,00",
            occurred_on=date(2026, 4, 1),
            category_id=c.id,
        )
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="out",
            amount="20,00",
            occurred_on=date(2026, 4, 10),
            category_id=c.id,
        )
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="out",
            amount="5,00",
            occurred_on=date(2026, 5, 1),
            category_id=c.id,
        )

        stats = category_stats(
            s, user_id=u.id, category_id=c.id, start=date(2026, 4, 1), end=date(2026, 4, 30)
        )
        assert stats["income_cents"] == 10000
        assert stats["expense_cents"] == 2000
        assert stats["net_cents"] == 8000
        assert stats["tx_count"] == 2
        assert len(stats["recent"]) == 2


def test_category_stats_rejects_inverted_period(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "inv-period@test.com", "Inv")
        c = create_category(s, user_id=u.id, name="Teste")
        with pytest.raises(ValueError):
            category_stats(s, user_id=u.id, category_id=c.id, start=date(2026, 4, 10), end=date(2026, 4, 1))
