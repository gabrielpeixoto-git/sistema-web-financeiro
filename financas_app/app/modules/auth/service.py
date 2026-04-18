from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from financas_app.app.common.errors import AuthError
from financas_app.app.common.security import (
    decode_token,
    hash_password,
    make_access_token,
    make_refresh_jwt,
    refresh_cookie_token,
    sha256_hex,
)
from financas_app.app.modules.auth import repo
from financas_app.app.modules.auth.models import PasswordResetToken, RefreshToken, User
from financas_app.app.modules.audit.service import log_action
from financas_app.app.settings import get_settings


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def register(session: Session, *, email: str, name: str, password: str) -> User:
    if repo.get_user_by_email(session, email):
        raise AuthError("email already registered")
    u = User(email=email, name=name, hashed_password=hash_password(password))
    session.add(u)
    session.commit()
    session.refresh(u)
    log_action(
        session,
        user_id=u.id,
        action="auth.register",
        entity="user",
        entity_id=u.id,
        detail=f"email={u.email}",
    )
    return u


def login(session: Session, *, email: str, password: str) -> User:
    u = repo.get_user_by_email(session, email)
    if not u:
        raise AuthError("invalid credentials")
    from financas_app.app.common.security import verify_password

    if not verify_password(password, u.hashed_password):
        raise AuthError("invalid credentials")
    log_action(
        session,
        user_id=u.id,
        action="auth.login",
        entity="user",
        entity_id=u.id,
        detail=f"email={u.email}",
    )
    return u


def issue_tokens(session: Session, *, user: User) -> tuple[str, str, str]:
    # returns: access_jwt, refresh_jwt, refresh_cookie_opaque
    now = datetime.now(UTC)
    refresh_id = uuid.uuid4().hex
    cookie_token = refresh_cookie_token()
    token_hash = sha256_hex(cookie_token)
    exp = now + timedelta(days=get_settings().refresh_token_expire_days)
    repo.add_refresh_token(
        session,
        RefreshToken(user_id=user.id, refresh_id=refresh_id, token_hash=token_hash, expires_at=exp),
    )
    session.commit()
    return make_access_token(user_id=user.id), make_refresh_jwt(user_id=user.id, refresh_id=refresh_id), cookie_token


def refresh(session: Session, *, refresh_jwt: str, refresh_cookie: str) -> tuple[str, str, str]:
    now = datetime.now(UTC)
    data = decode_token(refresh_jwt)
    if data.get("typ") != "refresh":
        raise AuthError("invalid refresh token")
    rid = data.get("rid")
    if not rid:
        raise AuthError("invalid refresh token")
    rt = repo.get_refresh_token(session, rid)
    if not rt or rt.revoked_at or _utc(rt.expires_at) <= now:
        raise AuthError("refresh token expired")
    if rt.token_hash != sha256_hex(refresh_cookie):
        raise AuthError("refresh token mismatch")

    # rotate
    repo.revoke_refresh_token(session, rt, now)
    session.commit()
    u = repo.get_user(session, rt.user_id)
    if not u:
        raise AuthError("user not found")
    return issue_tokens(session, user=u)


def user_from_access(session: Session, access_jwt: str) -> User:
    data = decode_token(access_jwt)
    if data.get("typ") != "access":
        raise AuthError("invalid access token")
    sub = data.get("sub")
    try:
        uid = int(sub)
    except Exception as e:  # noqa: BLE001
        raise AuthError("invalid access token") from e
    u = repo.get_user(session, uid)
    if not u:
        raise AuthError("user not found")
    return u


def request_password_reset(session: Session, *, email: str) -> str | None:
    """Returns opaque token if user exists; otherwise None (caller should not leak existence)."""
    u = repo.get_user_by_email(session, email)
    if not u:
        return None
    now = datetime.now(UTC)
    token = refresh_cookie_token()
    exp = now + timedelta(minutes=get_settings().password_reset_expire_minutes)
    repo.add_password_reset_token(
        session,
        PasswordResetToken(user_id=u.id, token_hash=sha256_hex(token), expires_at=exp),
    )
    session.commit()
    log_action(
        session,
        user_id=u.id,
        action="auth.password_reset.request",
        entity="user",
        entity_id=u.id,
        detail="",
    )
    return token


def reset_password(session: Session, *, token: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise AuthError("weak password")
    now = datetime.now(UTC)
    th = sha256_hex(token)
    prt = repo.get_password_reset_by_hash(session, th)
    if not prt or prt.used_at or _utc(prt.expires_at) <= now:
        raise AuthError("invalid reset token")
    u = repo.get_user(session, prt.user_id)
    if not u:
        raise AuthError("user not found")
    u.hashed_password = hash_password(new_password)
    session.add(u)
    repo.mark_password_reset_used(session, prt, now)
    session.commit()
    log_action(
        session,
        user_id=u.id,
        action="auth.password_reset.complete",
        entity="user",
        entity_id=u.id,
        detail="",
    )

