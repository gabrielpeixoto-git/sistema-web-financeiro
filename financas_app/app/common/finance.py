from __future__ import annotations

from datetime import date

from sqlmodel import Session, func, select

from financas_app.app.modules.transactions.models import Transaction


def period_filters(*, start: date | None = None, end: date | None = None) -> list:
    filters = []
    if start is not None:
        filters.append(Transaction.occurred_on >= start)
    if end is not None:
        filters.append(Transaction.occurred_on <= end)
    return filters


def sum_by_kind(
    session: Session,
    *,
    user_id: int,
    kind: str,
    category_id: int | None = None,
    account_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
) -> int:
    q_filters = [Transaction.user_id == user_id, Transaction.kind == kind, *period_filters(start=start, end=end)]
    if category_id is not None:
        q_filters.append(Transaction.category_id == category_id)
    if account_id is not None:
        q_filters.append(Transaction.account_id == account_id)
    q = select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(*q_filters)
    return int(session.exec(q).one())


def count_transactions(
    session: Session,
    *,
    user_id: int,
    category_id: int | None = None,
    account_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
) -> int:
    q_filters = [Transaction.user_id == user_id, *period_filters(start=start, end=end)]
    if category_id is not None:
        q_filters.append(Transaction.category_id == category_id)
    if account_id is not None:
        q_filters.append(Transaction.account_id == account_id)
    q = select(func.count(Transaction.id)).where(*q_filters)
    return int(session.exec(q).one())
