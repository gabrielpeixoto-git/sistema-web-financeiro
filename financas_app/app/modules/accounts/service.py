from __future__ import annotations

from sqlmodel import Session

from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.accounts import repo
from financas_app.app.modules.accounts.models import Account


def create_account(session: Session, *, name: str, currency: str, user_id: int) -> Account:
    account = Account(name=name, currency=currency, user_id=user_id)
    session.add(account)
    session.commit()
    session.refresh(account)
    log_action(
        session,
        user_id=user_id,
        action="accounts.create",
        entity="account",
        entity_id=account.id,
        detail=f"name={account.name}",
    )
    return account


def list_accounts(session: Session, *, user_id: int) -> list[Account]:
    return repo.list_accounts(session, user_id)
