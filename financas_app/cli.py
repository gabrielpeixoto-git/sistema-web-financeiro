"""CLI commands for the Finanças App."""

from __future__ import annotations

import sys
from sqlmodel import Session, create_engine

from financas_app.app.modules.notifications.email_reminders import (
    run_email_reminders_for_all,
)
from financas_app.app.settings import get_settings


def send_email_reminders() -> int:
    """Send email reminders to all users with upcoming bills.

    Usage: python -m financas_app.cli send-email-reminders
    """
    s = get_settings()
    if not s.smtp_host:
        print("SMTP not configured. Set SMTP_HOST env var.")
        return 1

    engine = create_engine(s.database_url, echo=False)
    with Session(engine) as session:
        result = run_email_reminders_for_all(session)
        print(f"Sent reminders to {result['sent_to_users']} of {result['total_users']} users")

    return 0


def main(args: list[str] | None = None) -> int:
    if args is None:
        args = sys.argv[1:]

    if not args:
        print("Usage: python -m financas_app.cli <command>")
        print("Commands: send-email-reminders")
        return 1

    cmd = args[0]
    if cmd == "send-email-reminders":
        return send_email_reminders()
    else:
        print(f"Unknown command: {cmd}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
