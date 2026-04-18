from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from financas_app.app.modules.auth.models import PasswordResetToken, RefreshToken, User


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def add_refresh_token(session: Session, rt: RefreshToken) -> None:
    session.add(rt)


def get_refresh_token(session: Session, refresh_id: str) -> RefreshToken | None:
    return session.exec(select(RefreshToken).where(RefreshToken.refresh_id == refresh_id)).first()


def revoke_refresh_token(session: Session, rt: RefreshToken, now: datetime) -> None:
    rt.revoked_at = now
    session.add(rt)


def add_password_reset_token(session: Session, prt: PasswordResetToken) -> None:
    session.add(prt)


def get_password_reset_by_hash(session: Session, token_hash: str) -> PasswordResetToken | None:
    return session.exec(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)).first()


def mark_password_reset_used(session: Session, prt: PasswordResetToken, now: datetime) -> None:
    prt.used_at = now
    session.add(prt)

