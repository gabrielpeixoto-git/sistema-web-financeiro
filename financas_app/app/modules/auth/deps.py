from __future__ import annotations

from urllib.parse import quote

from fastapi import Cookie, Depends, HTTPException, Request
from sqlmodel import Session

from financas_app.app.common.errors import AuthError
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.auth.service import user_from_access


def get_current_user(
    session: Session = Depends(get_session),
    access_token: str | None = Cookie(default=None),
) -> User:
    if not access_token:
        raise AuthError("missing access token")
    try:
        return user_from_access(session, access_token)
    except ValueError as e:
        raise AuthError("invalid access token") from e


def get_current_user_optional(
    session: Session = Depends(get_session),
    access_token: str | None = Cookie(default=None),
) -> User | None:
    if not access_token:
        return None
    try:
        return user_from_access(session, access_token)
    except (AuthError, ValueError):
        return None


_NEED_LOGIN_MSG = "Você precisa estar logado para acessar esta página."


def _login_redirect_headers(request: Request) -> dict[str, str]:
    target = f"/auth/login?msg={quote(_NEED_LOGIN_MSG)}"
    headers = {"Location": target}
    if request.headers.get("HX-Request", "").lower() == "true":
        headers["HX-Redirect"] = target
    return headers


def require_user_redirect(
    request: Request,
    session: Session = Depends(get_session),
    access_token: str | None = Cookie(default=None),
) -> User:
    if not access_token:
        raise HTTPException(status_code=303, headers=_login_redirect_headers(request))
    try:
        return user_from_access(session, access_token)
    except (AuthError, ValueError):
        raise HTTPException(status_code=303, headers=_login_redirect_headers(request))

