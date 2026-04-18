from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, func, select

from financas_app.app.common.dates import today_in_app
from financas_app.app.common.money import cents_to_brl
from financas_app.app.modules.auth.repo import get_user
from financas_app.app.modules.budgets.service import list_rows as budget_rows
from financas_app.app.modules.dashboard.service import summary
from financas_app.app.modules.goals.repo import list_active as active_goals
from financas_app.app.modules.notifications.models import Notification


def create_notification(session: Session, *, user_id: int, kind: str, message: str) -> Notification:
    n = Notification(user_id=user_id, kind=kind.strip(), message=message.strip())
    session.add(n)
    session.commit()
    session.refresh(n)
    return n


def list_notifications(session: Session, *, user_id: int, limit: int = 50) -> list[Notification]:
    q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list(session.exec(q))


def list_kinds(session: Session, *, user_id: int) -> list[str]:
    q = (
        select(Notification.kind)
        .where(Notification.user_id == user_id)
        .group_by(Notification.kind)
        .order_by(Notification.kind)
    )
    return [str(k) for k in session.exec(q).all()]


def list_notifications_filtered(
    session: Session, *, user_id: int, kind: str | None, limit: int = 100
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if kind:
        q = q.where(Notification.kind == kind)
    q = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    return list(session.exec(q))


def mark_read(session: Session, *, user_id: int, notification_id: int) -> None:
    n = session.exec(
        select(Notification).where(Notification.user_id == user_id, Notification.id == notification_id)
    ).first()
    if not n:
        return
    n.read_at = datetime.now(UTC)
    session.add(n)
    session.commit()


def mark_all_read(session: Session, *, user_id: int) -> int:
    now = datetime.now(UTC)
    rows = session.exec(
        select(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ).all()
    for n in rows:
        n.read_at = now
        session.add(n)
    session.commit()
    return len(rows)


def build_daily_summary_message(session: Session, *, user_id: int) -> str:
    s = summary(session, user_id=user_id)
    return (
        f"Resumo: receitas {cents_to_brl(s.income_cents)}, despesas {cents_to_brl(s.expense_cents)}, "
        f"resultado {cents_to_brl(s.balance_cents)}, lançamentos {s.tx_count}."
    )


def _exists_recent(session: Session, *, user_id: int, kind: str, message: str, since: datetime) -> bool:
    q = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.kind == kind,
        Notification.message == message,
        Notification.created_at >= since,
    )
    return int(session.exec(q).one()) > 0


def _budget_over_messages(session: Session, *, user_id: int, today: date) -> list[str]:
    rows = budget_rows(session, user_id=user_id, year=today.year, month=today.month)
    out: list[str] = []
    for r in rows:
        if r.limit_cents > 0 and r.spent_cents > r.limit_cents:
            out.append(
                f"Orçamento estourado em {r.category_name}: {cents_to_brl(r.spent_cents)} de "
                f"{cents_to_brl(r.limit_cents)} neste mês."
            )
    return out


def _budget_near_limit_messages(session: Session, *, user_id: int, today: date, pct_threshold: int = 80) -> list[str]:
    rows = budget_rows(session, user_id=user_id, year=today.year, month=today.month)
    out: list[str] = []
    for r in rows:
        if r.limit_cents <= 0 or r.spent_cents > r.limit_cents:
            continue
        pct = int(r.spent_cents * 100 / r.limit_cents)
        if pct >= pct_threshold:
            out.append(
                f"Orçamento próximo do limite em {r.category_name}: {cents_to_brl(r.spent_cents)} de "
                f"{cents_to_brl(r.limit_cents)} ({pct}% do orçamento neste mês)."
            )
    return out


def _goal_overdue_messages(session: Session, *, user_id: int, today: date) -> list[str]:
    out: list[str] = []
    for g in active_goals(session, user_id):
        if g.due_on and g.due_on < today and g.saved_cents < g.target_cents:
            out.append(
                f"Meta atrasada: {g.name} (prazo {g.due_on.isoformat()}) — "
                f"{cents_to_brl(g.saved_cents)} de {cents_to_brl(g.target_cents)}."
            )
    return out


def _goal_near_complete_messages(session: Session, *, user_id: int, pct_threshold: int = 80) -> list[str]:
    out: list[str] = []
    for g in active_goals(session, user_id):
        if g.target_cents <= 0 or g.saved_cents >= g.target_cents:
            continue
        pct = int(g.saved_cents * 100 / g.target_cents)
        if pct >= pct_threshold:
            out.append(
                f"Meta quase atingida: {g.name} — {cents_to_brl(g.saved_cents)} de "
                f"{cents_to_brl(g.target_cents)} ({pct}% do alvo)."
            )
    return out


def generate_for_user(
    session: Session,
    *,
    user_id: int,
    budget_near_pct: int = 80,
    goal_near_pct: int = 80,
    dedupe_hours: int = 24,
) -> int:
    u = get_user(session, user_id)
    tz = u.timezone if u else None
    today = today_in_app(tz)
    since = datetime.now(UTC) - timedelta(hours=dedupe_hours)

    created = 0
    msg = build_daily_summary_message(session, user_id=user_id)
    if not _exists_recent(session, user_id=user_id, kind="daily_summary", message=msg, since=since):
        create_notification(session, user_id=user_id, kind="daily_summary", message=msg)
        created += 1

    for m in _budget_over_messages(session, user_id=user_id, today=today):
        if not _exists_recent(session, user_id=user_id, kind="budget_over", message=m, since=since):
            create_notification(session, user_id=user_id, kind="budget_over", message=m)
            created += 1

    for m in _budget_near_limit_messages(session, user_id=user_id, today=today, pct_threshold=budget_near_pct):
        if not _exists_recent(session, user_id=user_id, kind="budget_near", message=m, since=since):
            create_notification(session, user_id=user_id, kind="budget_near", message=m)
            created += 1

    for m in _goal_overdue_messages(session, user_id=user_id, today=today):
        if not _exists_recent(session, user_id=user_id, kind="goal_overdue", message=m, since=since):
            create_notification(session, user_id=user_id, kind="goal_overdue", message=m)
            created += 1

    for m in _goal_near_complete_messages(session, user_id=user_id, pct_threshold=goal_near_pct):
        if not _exists_recent(session, user_id=user_id, kind="goal_near", message=m, since=since):
            create_notification(session, user_id=user_id, kind="goal_near", message=m)
            created += 1

    return created

