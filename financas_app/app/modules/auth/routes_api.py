from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request
from starlette.responses import JSONResponse, Response

from financas_app.app.common.rate_limit import enforce_rate_limit
from financas_app.app.common.security import is_dev
from financas_app.app.deps import get_session
from financas_app.app.modules.auth import service
from financas_app.app.settings import get_settings
from sqlmodel import Session

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookies(resp: Response, *, access: str, refresh: str, refresh_cookie: str) -> None:
    secure = not is_dev()
    resp.set_cookie("access_token", access, httponly=True, secure=secure, samesite="lax", path="/")
    resp.set_cookie("refresh_jwt", refresh, httponly=True, secure=secure, samesite="lax", path="/")
    resp.set_cookie("refresh_cookie", refresh_cookie, httponly=True, secure=secure, samesite="lax", path="/")


@router.post("/refresh")
def refresh(
    request: Request,
    session: Session = Depends(get_session),
    refresh_jwt: str | None = Cookie(default=None),
    refresh_cookie: str | None = Cookie(default=None),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="auth.refresh",
        limit=s.rate_limit_refresh_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    if not refresh_jwt or not refresh_cookie:
        resp = JSONResponse({"ok": False}, status_code=401)
        for key, value in rl_headers.items():
            resp.headers[key] = value
        return resp
    access, refresh2, cookie2 = service.refresh(
        session, refresh_jwt=refresh_jwt, refresh_cookie=refresh_cookie
    )
    resp = JSONResponse({"ok": True})
    _set_auth_cookies(resp, access=access, refresh=refresh2, refresh_cookie=cookie2)
    for key, value in rl_headers.items():
        resp.headers[key] = value
    return resp

