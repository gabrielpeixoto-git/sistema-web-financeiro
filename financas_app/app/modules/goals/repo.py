from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.goals.models import FinancialGoal


def list_active(session: Session, user_id: int) -> list[FinancialGoal]:
    q = (
        select(FinancialGoal)
        .where(FinancialGoal.user_id == user_id, FinancialGoal.active.is_(True))
        .order_by(FinancialGoal.id)
    )
    return list(session.exec(q))


def get(session: Session, user_id: int, goal_id: int) -> FinancialGoal | None:
    return session.exec(
        select(FinancialGoal).where(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id)
    ).first()


def add(session: Session, g: FinancialGoal) -> None:
    session.add(g)
