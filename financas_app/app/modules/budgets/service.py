from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, func, select

from financas_app.app.common.money import cents_to_brl, parse_brl_to_cents
from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.budgets import repo
from financas_app.app.modules.budgets.models import Budget
from financas_app.app.modules.categories.repo import get_category
from financas_app.app.modules.transactions.models import Transaction


@dataclass
class BudgetRow:
    budget_id: int
    category_id: int
    category_name: str
    limit_cents: int
    spent_cents: int


def month_bounds(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


def spent_in_category_month(
    session: Session, *, user_id: int, category_id: int, year: int, month: int
) -> int:
    start, end = month_bounds(year, month)
    q = select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
        Transaction.user_id == user_id,
        Transaction.category_id == category_id,
        Transaction.kind == "out",
        Transaction.occurred_on >= start,
        Transaction.occurred_on <= end,
    )
    return int(session.exec(q).one())


def list_rows(session: Session, *, user_id: int, year: int, month: int) -> list[BudgetRow]:
    from financas_app.app.modules.categories.models import Category

    rows: list[BudgetRow] = []
    for b in repo.list_for_month(session, user_id, year, month):
        cat = session.get(Category, b.category_id)
        name = cat.name if cat else "?"
        spent = spent_in_category_month(
            session, user_id=user_id, category_id=b.category_id, year=year, month=month
        )
        rows.append(
            BudgetRow(
                budget_id=b.id,
                category_id=b.category_id,
                category_name=name,
                limit_cents=b.limit_cents,
                spent_cents=spent,
            )
        )
    return rows


def upsert_budget(
    session: Session,
    *,
    user_id: int,
    category_id: int,
    year: int,
    month: int,
    amount: str,
) -> Budget:
    if not (1 <= month <= 12):
        raise ValueError("invalid month")
    if not get_category(session, user_id, category_id):
        raise ValueError("invalid category")
    limit_cents = parse_brl_to_cents(amount)
    if limit_cents <= 0:
        raise ValueError("amount must be > 0")

    existing = repo.get_by_user_cat_month(session, user_id, category_id, year, month)
    if existing:
        existing.limit_cents = limit_cents
        session.add(existing)
        session.commit()
        session.refresh(existing)
        log_action(
            session,
            user_id=user_id,
            action="budgets.update",
            entity="budget",
            entity_id=existing.id,
            detail=f"y={year};m={month};cents={limit_cents}",
        )
        return existing

    b = Budget(
        user_id=user_id,
        category_id=category_id,
        year=year,
        month=month,
        limit_cents=limit_cents,
    )
    repo.add(session, b)
    session.commit()
    session.refresh(b)
    log_action(
        session,
        user_id=user_id,
        action="budgets.create",
        entity="budget",
        entity_id=b.id,
        detail=f"y={year};m={month};cents={limit_cents}",
    )
    return b


def delete_budget(session: Session, *, user_id: int, budget_id: int) -> None:
    b = repo.get(session, user_id, budget_id)
    if not b:
        raise ValueError("not found")
    bid = b.id
    session.delete(b)
    session.commit()
    log_action(
        session,
        user_id=user_id,
        action="budgets.delete",
        entity="budget",
        entity_id=bid,
        detail="",
    )


def format_row_br(row: BudgetRow) -> tuple[str, str, str, int]:
    lim = cents_to_brl(row.limit_cents)
    sp = cents_to_brl(row.spent_cents)
    rem = cents_to_brl(row.limit_cents - row.spent_cents)
    if row.limit_cents <= 0:
        pct = 0
    else:
        pct = min(999, int(row.spent_cents * 100 / row.limit_cents))
    return lim, sp, rem, pct
