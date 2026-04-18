from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.recurring.models import RecurringRule


def list_active(session: Session, user_id: int) -> list[RecurringRule]:
    q = (
        select(RecurringRule)
        .where(RecurringRule.user_id == user_id, RecurringRule.active.is_(True))
        .order_by(RecurringRule.next_due, RecurringRule.id)
    )
    return list(session.exec(q))


def get(session: Session, user_id: int, rule_id: int) -> RecurringRule | None:
    return session.exec(
        select(RecurringRule).where(RecurringRule.id == rule_id, RecurringRule.user_id == user_id)
    ).first()


def add(session: Session, r: RecurringRule) -> None:
    session.add(r)
