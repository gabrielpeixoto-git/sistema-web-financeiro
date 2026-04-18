from __future__ import annotations

from sqlmodel import Session, case, func, select

from financas_app.app.modules.transactions.models import Transaction


def list_transactions(session: Session, user_id: int, *, limit: int = 50) -> list[Transaction]:
    q = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
        .limit(limit)
    )
    return list(session.exec(q))


def add(session: Session, t: Transaction) -> None:
    session.add(t)


def exists_duplicate(
    session: Session,
    *,
    user_id: int,
    account_id: int,
    category_id: int | None,
    kind: str,
    amount_cents: int,
    occurred_on,
    description: str,
) -> bool:
    q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.account_id == account_id,
        Transaction.category_id == category_id,
        Transaction.kind == kind,
        Transaction.amount_cents == amount_cents,
        Transaction.occurred_on == occurred_on,
        Transaction.description == description,
    )
    return session.exec(q).first() is not None


def balance_for_account(session: Session, user_id: int, account_id: int) -> int:
    q = select(
        func.coalesce(
            func.sum(
                case((Transaction.kind == "in", Transaction.amount_cents), else_=-Transaction.amount_cents)
            ),
            0,
        )
    ).where(Transaction.user_id == user_id, Transaction.account_id == account_id)
    return int(session.exec(q).one())


def balance_total(session: Session, user_id: int) -> int:
    q = select(
        func.coalesce(
            func.sum(
                case((Transaction.kind == "in", Transaction.amount_cents), else_=-Transaction.amount_cents)
            ),
            0,
        )
    ).where(Transaction.user_id == user_id)
    return int(session.exec(q).one())

