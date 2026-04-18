from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, case, func, select

from financas_app.app.common.dates import ensure_period_valid
from financas_app.app.common.finance import count_transactions, sum_by_kind
from financas_app.app.modules.transactions.models import Transaction


@dataclass
class PeriodReport:
    start: date
    end: date
    income_cents: int
    expense_cents: int
    net_cents: int
    count: int


def period_report(session: Session, *, user_id: int, start: date, end: date, account_id: int | None = None, category_id: int | None = None) -> PeriodReport:
    ensure_period_valid(start, end)
    income = sum_by_kind(session, user_id=user_id, kind="in", start=start, end=end, account_id=account_id, category_id=category_id)
    expense = sum_by_kind(session, user_id=user_id, kind="out", start=start, end=end, account_id=account_id, category_id=category_id)
    count = count_transactions(session, user_id=user_id, start=start, end=end, account_id=account_id, category_id=category_id)
    return PeriodReport(
        start=start,
        end=end,
        income_cents=income,
        expense_cents=expense,
        net_cents=income - expense,
        count=count,
    )


def period_by_kind(session: Session, *, user_id: int, start: date, end: date, account_id: int | None = None, category_id: int | None = None) -> list[tuple[str, int]]:
    ensure_period_valid(start, end)
    q = (
        select(
            Transaction.kind,
            func.coalesce(func.sum(Transaction.amount_cents), 0),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.occurred_on >= start, Transaction.occurred_on <= end)
    )
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if category_id:
        q = q.where(Transaction.category_id == category_id)
    q = q.group_by(Transaction.kind).order_by(Transaction.kind)
    return [(str(kind), int(total)) for kind, total in session.exec(q).all()]


def period_by_category(
    session: Session, *, user_id: int, start: date, end: date, kind: str | None = None, account_id: int | None = None
) -> list[tuple[str, int]]:
    """Get totals by category for period. Optionally filter by kind (in/out)."""
    from financas_app.app.modules.categories.models import Category

    ensure_period_valid(start, end)

    q = (
        select(
            func.coalesce(Category.name, "(sem categoria)"),
            func.coalesce(func.sum(Transaction.amount_cents), 0),
        )
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .where(Transaction.user_id == user_id)
        .where(Transaction.occurred_on >= start, Transaction.occurred_on <= end)
    )

    if kind:
        q = q.where(Transaction.kind == kind)
    if account_id:
        q = q.where(Transaction.account_id == account_id)

    q = q.group_by(Category.name).order_by(func.sum(Transaction.amount_cents).desc())

    return [(str(name), int(total)) for name, total in session.exec(q).all()]


def monthly_trend(
    session: Session, *, user_id: int, start: date, end: date, account_id: int | None = None, category_id: int | None = None
) -> list[tuple[str, int, int]]:
    """Get income and expense per month for trend chart."""
    ensure_period_valid(start, end)

    # Use to_char for PostgreSQL compatibility
    month_expr = func.to_char(Transaction.occurred_on, "YYYY-MM").label("month")

    q = (
        select(
            month_expr,
            func.coalesce(
                func.sum(case((Transaction.kind == "in", Transaction.amount_cents), else_=0)), 0
            ).label("income"),
            func.coalesce(
                func.sum(case((Transaction.kind == "out", Transaction.amount_cents), else_=0)), 0
            ).label("expense"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.occurred_on >= start, Transaction.occurred_on <= end)
    )

    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if category_id:
        q = q.where(Transaction.category_id == category_id)

    q = q.group_by(month_expr).order_by(month_expr)

    return [(str(row.month), int(row.income), int(row.expense)) for row in session.exec(q).all()]

