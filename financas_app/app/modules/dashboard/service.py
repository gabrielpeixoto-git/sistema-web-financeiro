from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, case, func, select

from financas_app.app.common.dates import first_day_of_month
from financas_app.app.common.finance import count_transactions, sum_by_kind
from financas_app.app.modules.transactions.models import Transaction


@dataclass
class DashboardSummary:
    income_cents: int
    expense_cents: int
    balance_cents: int
    tx_count: int


@dataclass
class MonthData:
    month_label: str
    balance_cents: int


def summary(session: Session, *, user_id: int) -> DashboardSummary:
    income = sum_by_kind(session, user_id=user_id, kind="in")
    expense = sum_by_kind(session, user_id=user_id, kind="out")
    count = count_transactions(session, user_id=user_id)
    return DashboardSummary(
        income_cents=income,
        expense_cents=expense,
        balance_cents=income - expense,
        tx_count=count,
    )


def balance_evolution(session: Session, *, user_id: int, months: int = 6) -> list[MonthData]:
    """Calculate running balance for the last N months."""
    from financas_app.app.common.dates import add_one_month, today_in_app

    today = today_in_app()
    result = []
    running_balance = 0

    # Start from months ago
    start_date = today.replace(day=1)
    for _ in range(months - 1):
        start_date = _subtract_one_month(start_date)

    # Calculate cumulative balance month by month
    current = start_date
    for _ in range(months):
        month_end = _last_day_of_month(current)

        # Income and expense for this month
        income = sum_by_kind(session, user_id=user_id, kind="in", start=current, end=month_end)
        expense = sum_by_kind(session, user_id=user_id, kind="out", start=current, end=month_end)

        running_balance += (income - expense)

        month_label = current.strftime("%b/%y")
        result.append(MonthData(month_label=month_label, balance_cents=running_balance))

        current = add_one_month(current)

    return result


def _subtract_one_month(d: date) -> date:
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=1)
    return d.replace(month=d.month - 1, day=1)


def _last_day_of_month(d: date) -> date:
    import calendar

    last = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last)


def by_category(session: Session, *, user_id: int) -> list[tuple[str, int]]:
    from financas_app.app.modules.categories.models import Category

    q = (
        select(
            func.coalesce(Category.name, "(sem categoria)"),
            func.coalesce(
                func.sum(
                    case((Transaction.kind == "in", Transaction.amount_cents), else_=-Transaction.amount_cents)
                ),
                0,
            ),
        )
        .select_from(Transaction)
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .where(Transaction.user_id == user_id)
        .group_by(Category.name)
        .order_by(func.abs(func.sum(Transaction.amount_cents)).desc())
    )
    return [(str(name), int(total)) for name, total in session.exec(q).all()]

