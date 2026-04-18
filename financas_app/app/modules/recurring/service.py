from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from financas_app.app.common.dates import advance_by_frequency
from financas_app.app.common.money import parse_brl_to_cents
from financas_app.app.modules.accounts.repo import get_account
from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.categories.repo import get_category
from financas_app.app.modules.recurring import repo as rrepo
from financas_app.app.modules.recurring.models import RecurringRule
from financas_app.app.modules.transactions import repo as trepo
from financas_app.app.modules.transactions.models import Transaction

_FREQ = frozenset({"daily", "weekly", "monthly"})
_MAX_STEPS = 500


def create_rule(
    session: Session,
    *,
    user_id: int,
    account_id: int,
    kind: str,
    amount: str,
    frequency: str,
    start_on: date,
    end_on: date | None = None,
    category_id: int | None = None,
    description: str = "",
) -> RecurringRule:
    if kind not in ("in", "out"):
        raise ValueError("invalid kind")
    if frequency not in _FREQ:
        raise ValueError("invalid frequency")
    if not get_account(session, user_id, account_id):
        raise ValueError("invalid account")
    if category_id is not None and not get_category(session, user_id, category_id):
        raise ValueError("invalid category")
    amount_cents = parse_brl_to_cents(amount)
    if amount_cents <= 0:
        raise ValueError("amount must be > 0")
    if end_on is not None and end_on < start_on:
        raise ValueError("invalid period")

    r = RecurringRule(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        kind=kind,
        amount_cents=amount_cents,
        description=(description or "").strip(),
        frequency=frequency,
        next_due=start_on,
        end_on=end_on,
        active=True,
    )
    rrepo.add(session, r)
    session.commit()
    session.refresh(r)
    log_action(
        session,
        user_id=user_id,
        action="recurring.create",
        entity="recurringrule",
        entity_id=r.id,
        detail=f"freq={frequency}",
    )
    return r


def deactivate(session: Session, *, user_id: int, rule_id: int) -> None:
    r = rrepo.get(session, user_id, rule_id)
    if not r:
        raise ValueError("not found")
    r.active = False
    session.add(r)
    session.commit()
    log_action(
        session,
        user_id=user_id,
        action="recurring.deactivate",
        entity="recurringrule",
        entity_id=rule_id,
        detail="",
    )


def _tx_exists(session: Session, *, rule_id: int, occurred_on: date) -> bool:
    q = select(Transaction.id).where(
        Transaction.recurring_rule_id == rule_id,
        Transaction.occurred_on == occurred_on,
    )
    return session.exec(q).first() is not None


def materialize_due(session: Session, *, user_id: int, until: date) -> int:
    created = 0
    for rule in rrepo.list_active(session, user_id):
        steps = 0
        while (
            rule.active
            and rule.next_due <= until
            and (rule.end_on is None or rule.next_due <= rule.end_on)
            and steps < _MAX_STEPS
        ):
            steps += 1
            due = rule.next_due
            if _tx_exists(session, rule_id=rule.id, occurred_on=due):
                rule.next_due = advance_by_frequency(due, rule.frequency)
                session.add(rule)
                session.commit()
                session.refresh(rule)
                continue

            t = Transaction(
                user_id=user_id,
                account_id=rule.account_id,
                category_id=rule.category_id,
                kind=rule.kind,
                amount_cents=rule.amount_cents,
                occurred_on=due,
                description=rule.description or "Recorrente",
                recurring_rule_id=rule.id,
            )
            trepo.add(session, t)
            rule.next_due = advance_by_frequency(due, rule.frequency)
            session.add(rule)
            session.commit()
            session.refresh(t)
            session.refresh(rule)
            log_action(
                session,
                user_id=user_id,
                action="recurring.materialize",
                entity="transaction",
                entity_id=t.id,
                detail=f"rule={rule.id};due={due.isoformat()}",
            )
            created += 1
    return created
