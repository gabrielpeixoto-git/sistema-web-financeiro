from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.accounts.models import Account


def list_accounts(session: Session, user_id: int) -> list[Account]:
    return list(session.exec(select(Account).where(Account.user_id == user_id).order_by(Account.id)))


def get_account(session: Session, user_id: int, account_id: int) -> Account | None:
    return session.exec(
        select(Account).where(Account.user_id == user_id, Account.id == account_id)
    ).first()


def get_account_by_name(session: Session, user_id: int, name: str) -> Account | None:
    return session.exec(
        select(Account).where(Account.user_id == user_id, Account.name == name.strip())
    ).first()


def add(session: Session, a: Account) -> None:
    session.add(a)

