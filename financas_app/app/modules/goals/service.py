from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session

from financas_app.app.common.money import cents_to_brl, parse_brl_to_cents
from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.goals import repo
from financas_app.app.modules.goals.models import FinancialGoal


@dataclass
class GoalRow:
    goal_id: int
    name: str
    target_cents: int
    saved_cents: int
    due_on: date | None


def create_goal(
    session: Session,
    *,
    user_id: int,
    name: str,
    target: str,
    due_on: date | None = None,
) -> FinancialGoal:
    nm = (name or "").strip()
    if not nm:
        raise ValueError("invalid name")
    target_cents = parse_brl_to_cents(target)
    if target_cents <= 0:
        raise ValueError("invalid target")

    g = FinancialGoal(
        user_id=user_id,
        name=nm[:120],
        target_cents=target_cents,
        saved_cents=0,
        due_on=due_on,
        active=True,
    )
    repo.add(session, g)
    session.commit()
    session.refresh(g)
    log_action(
        session,
        user_id=user_id,
        action="goals.create",
        entity="financial_goal",
        entity_id=g.id,
        detail=f"target_cents={target_cents}",
    )
    return g


def list_rows(session: Session, *, user_id: int) -> list[GoalRow]:
    rows: list[GoalRow] = []
    for g in repo.list_active(session, user_id):
        rows.append(
            GoalRow(
                goal_id=g.id,
                name=g.name,
                target_cents=g.target_cents,
                saved_cents=g.saved_cents,
                due_on=g.due_on,
            )
        )
    return rows


def format_row(gr: GoalRow) -> dict[str, object]:
    tgt = cents_to_brl(gr.target_cents)
    sv = cents_to_brl(gr.saved_cents)
    rem_cents = max(0, gr.target_cents - gr.saved_cents)
    remaining = cents_to_brl(rem_cents)
    if gr.target_cents <= 0:
        pct = 0
    else:
        pct = min(999, int(gr.saved_cents * 100 / gr.target_cents))
    return {
        "name": gr.name,
        "target": tgt,
        "saved": sv,
        "remaining": remaining,
        "pct": pct,
        "bar_pct": min(pct, 100),
        "goal_id": gr.goal_id,
        "done": gr.saved_cents >= gr.target_cents,
        "due_on": gr.due_on.isoformat() if gr.due_on else "",
    }


def add_progress(
    session: Session,
    *,
    user_id: int,
    goal_id: int,
    amount: str,
) -> FinancialGoal:
    g = repo.get(session, user_id, goal_id)
    if not g or not g.active:
        raise ValueError("not found")
    delta = parse_brl_to_cents(amount)
    if delta <= 0:
        raise ValueError("invalid amount")
    g.saved_cents = g.saved_cents + delta
    session.add(g)
    session.commit()
    session.refresh(g)
    log_action(
        session,
        user_id=user_id,
        action="goals.add_progress",
        entity="financial_goal",
        entity_id=g.id,
        detail=f"delta_cents={delta};saved={g.saved_cents}",
    )
    return g


def deactivate(session: Session, *, user_id: int, goal_id: int) -> None:
    g = repo.get(session, user_id, goal_id)
    if not g:
        raise ValueError("not found")
    g.active = False
    session.add(g)
    session.commit()
    log_action(
        session,
        user_id=user_id,
        action="goals.deactivate",
        entity="financial_goal",
        entity_id=goal_id,
        detail="",
    )
