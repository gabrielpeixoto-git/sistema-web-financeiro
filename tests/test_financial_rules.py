from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.transactions.service import (
    balance_for_account,
    balance_total,
    create_transaction,
    create_transfer,
)


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fin_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str, name: str, user_id: int | None = None) -> User:
    u = User(id=user_id, email=email, name=name, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_balance_is_consistent(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "u1@test.com", "U1")
        a = create_account(s, currency="BRL", user_id=u.id, name="Nubank")

        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="100,00",
            occurred_on=date(2026, 4, 15),
        )
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="out",
            amount="30,50",
            occurred_on=date(2026, 4, 15),
        )

        assert balance_for_account(s, user_id=u.id, account_id=a.id) == 6950
        assert balance_total(s, user_id=u.id) == 6950


def test_user_cannot_post_into_other_user_account(tmp_path):
    with _session(tmp_path) as s:
        u1 = _user(s, "u1@test.com", "U1")
        u2 = _user(s, "u2@test.com", "U2")
        a2 = create_account(s, currency="BRL", user_id=u2.id, name="Conta U2")

        try:
            create_transaction(
                s,
                user_id=u1.id,
                account_id=a2.id,
                kind="out",
                amount="10,00",
                occurred_on=date(2026, 4, 15),
            )
        except ValueError as e:
            assert str(e) == "invalid account"
        else:
            assert False, "expected ValueError"


def test_transfer_moves_balance_between_accounts(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "xfer1@test.com", "U1")
        a = create_account(s, currency="BRL", user_id=u.id, name="A")
        b = create_account(s, currency="BRL", user_id=u.id, name="B")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="100,00",
            occurred_on=date(2026, 4, 15),
        )
        create_transfer(
            s,
            user_id=u.id,
            from_account_id=a.id,
            to_account_id=b.id,
            amount="40,00",
            occurred_on=date(2026, 4, 16),
        )
        assert balance_for_account(s, user_id=u.id, account_id=a.id) == 6000
        assert balance_for_account(s, user_id=u.id, account_id=b.id) == 4000
        assert balance_total(s, user_id=u.id) == 10000


def test_transfer_rejects_insufficient_balance(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "xfer2@test.com", "U1")
        a = create_account(s, currency="BRL", user_id=u.id, name="A")
        b = create_account(s, currency="BRL", user_id=u.id, name="B")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="10,00",
            occurred_on=date(2026, 4, 15),
        )
        try:
            create_transfer(
                s,
                user_id=u.id,
                from_account_id=a.id,
                to_account_id=b.id,
                amount="50,00",
                occurred_on=date(2026, 4, 15),
            )
        except ValueError as e:
            assert str(e) == "insufficient balance"
        else:
            assert False, "expected ValueError"


def test_transfer_rejects_same_account(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "xfer3@test.com", "U1")
        a = create_account(s, currency="BRL", user_id=u.id, name="A")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="10,00",
            occurred_on=date(2026, 4, 15),
        )
        try:
            create_transfer(
                s,
                user_id=u.id,
                from_account_id=a.id,
                to_account_id=a.id,
                amount="5,00",
                occurred_on=date(2026, 4, 15),
            )
        except ValueError as e:
            assert str(e) == "same account"
        else:
            assert False, "expected ValueError"


def test_transfer_rejects_foreign_account(tmp_path):
    with _session(tmp_path) as s:
        u1 = _user(s, "xfer4a@test.com", "U1")
        u2 = _user(s, "xfer4b@test.com", "U2")
        a1 = create_account(s, currency="BRL", user_id=u1.id, name="A1")
        a2 = create_account(s, currency="BRL", user_id=u2.id, name="A2")
        create_transaction(
            s,
            user_id=u1.id,
            account_id=a1.id,
            kind="in",
            amount="100,00",
            occurred_on=date(2026, 4, 15),
        )
        try:
            create_transfer(
                s,
                user_id=u1.id,
                from_account_id=a1.id,
                to_account_id=a2.id,
                amount="10,00",
                occurred_on=date(2026, 4, 15),
            )
        except ValueError as e:
            assert str(e) == "invalid account"
        else:
            assert False, "expected ValueError"