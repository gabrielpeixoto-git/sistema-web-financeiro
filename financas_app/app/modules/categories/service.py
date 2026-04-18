from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from financas_app.app.common.dates import ensure_period_valid
from financas_app.app.common.finance import count_transactions, period_filters, sum_by_kind
from financas_app.app.common.money import cents_to_brl

from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.categories import repo
from financas_app.app.modules.categories.models import Category
from financas_app.app.modules.transactions.models import Transaction


def create_category(session: Session, *, user_id: int, name: str) -> Category:
    c = Category(user_id=user_id, name=name.strip())
    repo.add(session, c)
    session.commit()
    session.refresh(c)
    log_action(
        session,
        user_id=user_id,
        action="categories.create",
        entity="category",
        entity_id=c.id,
        detail=f"name={c.name}",
    )
    return c


def list_categories(session: Session, *, user_id: int) -> list[Category]:
    return repo.list_categories(session, user_id)


def category_stats(
    session: Session,
    *,
    user_id: int,
    category_id: int,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    c = repo.get_category(session, user_id, category_id)
    if not c:
        raise ValueError("category not found")

    if start is not None and end is not None:
        ensure_period_valid(start, end)

    period_filter = period_filters(start=start, end=end)
    income = sum_by_kind(
        session, user_id=user_id, category_id=category_id, kind="in", start=start, end=end
    )
    expense = sum_by_kind(
        session, user_id=user_id, category_id=category_id, kind="out", start=start, end=end
    )
    tx_count = count_transactions(
        session, user_id=user_id, category_id=category_id, start=start, end=end
    )

    recent_q = (
        select(Transaction)
        .where(Transaction.user_id == user_id, Transaction.category_id == category_id, *period_filter)
        .order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
        .limit(10)
    )
    recent = [
        {
            "occurred_on": t.occurred_on,
            "kind": t.kind,
            "amount": cents_to_brl(t.amount_cents),
            "description": t.description,
        }
        for t in session.exec(recent_q).all()
    ]
    return {
        "category": c,
        "income_cents": income,
        "expense_cents": expense,
        "net_cents": income - expense,
        "tx_count": tx_count,
        "recent": recent,
    }

