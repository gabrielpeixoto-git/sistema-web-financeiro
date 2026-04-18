from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Protocol

from sqlmodel import Session, select

from financas_app.app.common.dates import today_in_app
from financas_app.app.common.email import build_reminder_email, get_sender
from financas_app.app.common.money import cents_to_brl
from financas_app.app.modules.accounts.repo import get_account
from financas_app.app.modules.auth.repo import get_user
from financas_app.app.modules.recurring.repo import list_active as list_recurring
from financas_app.app.settings import get_settings


class ReminderItem(Protocol):
    due_date: date
    description: str
    amount_cents: int
    account_id: int


def _build_items(
    session: Session,
    *,
    user_id: int,
    today: date,
    days_before: int,
) -> list[dict]:
    """Collect upcoming bills from recurring rules and future transactions."""
    items: list[dict] = []
    seen_keys: set[str] = set()

    # Check recurring rules
    for rule in list_recurring(session, user_id):
        if not rule.active or rule.kind != "out":
            continue
        # Calculate due dates within the window
        current = rule.next_due
        end_date = today + timedelta(days=days_before)
        while current <= end_date:
            if current >= today:
                key = f"rec:{rule.id}:{current.isoformat()}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    acc = get_account(session, user_id, rule.account_id)
                    items.append({
                        "due_date": current.isoformat(),
                        "description": rule.description or "Recorrente",
                        "amount": cents_to_brl(rule.amount_cents),
                        "amount_cents": rule.amount_cents,
                        "account": acc.name if acc else "Conta",
                        "account_id": rule.account_id,
                        "source": "recurring",
                        "source_id": rule.id,
                    })
            current += timedelta(days=1)
            # Safety limit
            if len(items) > 100:
                break

    return sorted(items, key=lambda x: (x["due_date"], x["description"]))


def _reminder_sent_recently(
    session: Session,
    *,
    user_id: int,
    since: datetime,
) -> bool:
    """Check if a reminder was already sent to this user recently."""
    from financas_app.app.modules.notifications.models import Notification

    q = select(Notification).where(
        Notification.user_id == user_id,
        Notification.kind == "email_reminder",
        Notification.created_at >= since,
    ).limit(1)
    return session.exec(q).first() is not None


def _record_reminder_sent(
    session: Session,
    *,
    user_id: int,
    item_count: int,
) -> None:
    """Record that a reminder was sent."""
    from financas_app.app.modules.notifications.models import Notification
    from financas_app.app.modules.notifications.service import create_notification

    create_notification(
        session,
        user_id=user_id,
        kind="email_reminder",
        message=f"Email de lembrete enviado com {item_count} conta(s) a pagar.",
    )


def send_email_reminders_for_user(
    session: Session,
    *,
    user_id: int,
    force: bool = False,
) -> dict[str, int | str]:
    """Send email reminder to user if they have upcoming bills."""
    s = get_settings()
    user = get_user(session, user_id)
    if not user or not user.email:
        return {"sent": 0, "reason": "no_email"}
    if not user.email_reminders_enabled:
        return {"sent": 0, "reason": "disabled_by_user"}

    # Check cooldown (unless forced)
    if not force:
        cooldown_hours = 24  # Don't spam, once per day max
        since = datetime.utcnow() - timedelta(hours=cooldown_hours)
        if _reminder_sent_recently(session, user_id=user_id, since=since):
            return {"sent": 0, "reason": "recently_sent"}

    today = today_in_app(user.timezone)
    items = _build_items(
        session,
        user_id=user_id,
        today=today,
        days_before=s.email_reminder_days_before,
    )

    if not items:
        return {"sent": 0, "reason": "no_upcoming_bills"}

    # Build and send email
    text, html = build_reminder_email(
        user_name=user.name or user.email.split("@")[0],
        items=items,
    )

    sender = get_sender()
    ok = sender.send(
        to=user.email,
        subject=f"Lembrete: {len(items)} conta(s) a pagar em breve",
        html=html,
        text=text,
    )

    if ok:
        _record_reminder_sent(session, user_id=user_id, item_count=len(items))

    return {"sent": 1 if ok else 0, "items": len(items)}


def run_email_reminders_for_all(
    session: Session,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Send email reminders to all users with upcoming bills."""
    from financas_app.app.modules.auth.models import User

    q = select(User.id)
    user_ids = list(session.exec(q).all())

    total_sent = 0
    total_users = 0
    for uid in user_ids:
        result = send_email_reminders_for_user(session, user_id=uid, force=force)
        if result.get("sent"):
            total_sent += 1
            total_users += 1

    return {"sent_to_users": total_sent, "total_users": len(user_ids)}
