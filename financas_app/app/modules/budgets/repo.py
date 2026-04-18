from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.budgets.models import Budget


def list_for_month(session: Session, user_id: int, year: int, month: int) -> list[Budget]:
    q = (
        select(Budget)
        .where(Budget.user_id == user_id, Budget.year == year, Budget.month == month)
        .order_by(Budget.category_id)
    )
    return list(session.exec(q))


def get_by_user_cat_month(
    session: Session, user_id: int, category_id: int, year: int, month: int
) -> Budget | None:
    return session.exec(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.year == year,
            Budget.month == month,
        )
    ).first()


def get(session: Session, user_id: int, budget_id: int) -> Budget | None:
    return session.exec(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    ).first()


def add(session: Session, b: Budget) -> None:
    session.add(b)
