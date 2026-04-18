from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from pathlib import Path
from starlette.templating import Jinja2Templates

from financas_app.app.common.errors import AuthError
from financas_app.app.common.rate_limit import enforce_rate_limit
from financas_app.app.common.security import is_dev
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import get_current_user_optional
from financas_app.app.modules.auth import service
from financas_app.app.settings import get_settings
from financas_app.app.modules.auth.models import User
from sqlmodel import Session

router = APIRouter(prefix="/auth", tags=["auth"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _set_rate_limit_headers(resp: Response, headers: dict[str, str]) -> None:
    for key, value in headers.items():
        resp.headers[key] = value


def _set_auth_cookies(resp: Response, *, access: str, refresh: str, refresh_cookie: str) -> None:
    secure = not is_dev()
    resp.set_cookie("access_token", access, httponly=True, secure=secure, samesite="lax", path="/")
    resp.set_cookie("refresh_jwt", refresh, httponly=True, secure=secure, samesite="lax", path="/")
    resp.set_cookie("refresh_cookie", refresh_cookie, httponly=True, secure=secure, samesite="lax", path="/")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    msg: str | None = Query(default=None),
    user: User | None = Depends(get_current_user_optional),
):
    if user:
        return RedirectResponse(url="/transactions", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"request": request, "msg": msg or ""})


@router.post("/login")
def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="auth.login",
        limit=s.rate_limit_auth_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    try:
        u = service.login(session, email=email, password=password)
    except AuthError:
        resp = templates.TemplateResponse(
            request,
            "auth/login.html",
            {"request": request, "msg": "Email ou senha inválidos."},
            status_code=401,
        )
        _set_rate_limit_headers(resp, rl_headers)
        return resp
    access, refresh, refresh_cookie = service.issue_tokens(session, user=u)
    resp = RedirectResponse(url="/", status_code=303)
    _set_auth_cookies(resp, access=access, refresh=refresh, refresh_cookie=refresh_cookie)
    _set_rate_limit_headers(resp, rl_headers)
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/transactions", status_code=303)
    return templates.TemplateResponse(request, "auth/register.html", {"request": request})


@router.get("/forgot", response_class=HTMLResponse)
def forgot_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/transactions", status_code=303)
    return templates.TemplateResponse(request, "auth/forgot.html", {"request": request})


@router.post("/forgot")
def forgot_action(
    request: Request,
    email: str = Form(...),
    session: Session = Depends(get_session),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="auth.forgot",
        limit=s.rate_limit_reset_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    token = service.request_password_reset(session, email=email)
    dev_hint = ""
    if token and is_dev():
        dev_hint = f" (dev) token={token}"
    resp = templates.TemplateResponse(
        request,
        "auth/forgot_done.html",
        {
            "request": request,
            "message": "Se o email existir, enviamos instruções para redefinir a senha." + dev_hint,
        },
    )
    _set_rate_limit_headers(resp, rl_headers)
    return resp


@router.get("/reset", response_class=HTMLResponse)
def reset_page(
    request: Request,
    token: str | None = None,
    user: User | None = Depends(get_current_user_optional),
):
    if user:
        return RedirectResponse(url="/transactions", status_code=303)
    return templates.TemplateResponse(request, "auth/reset.html", {"request": request, "token": token or ""})


@router.post("/reset")
def reset_action(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="auth.reset",
        limit=s.rate_limit_reset_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    try:
        service.reset_password(session, token=token, new_password=password)
    except AuthError:
        resp = templates.TemplateResponse(
            request,
            "auth/reset.html",
            {"request": request, "token": token, "error": "Token inválido ou expirado."},
            status_code=400,
        )
        _set_rate_limit_headers(resp, rl_headers)
        return resp
    resp = RedirectResponse(url="/auth/login", status_code=303)
    _set_rate_limit_headers(resp, rl_headers)
    return resp


@router.post("/register")
def register_action(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="auth.register",
        limit=s.rate_limit_auth_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    try:
        u = service.register(session, email=email, name=name, password=password)
    except AuthError:
        resp = templates.TemplateResponse(
            request,
            "auth/register.html",
            {"request": request, "msg": "Não foi possível criar a conta com esses dados."},
            status_code=400,
        )
        _set_rate_limit_headers(resp, rl_headers)
        return resp
    access, refresh, refresh_cookie = service.issue_tokens(session, user=u)
    resp = RedirectResponse(url="/", status_code=303)
    _set_auth_cookies(resp, access=access, refresh=refresh, refresh_cookie=refresh_cookie)
    _set_rate_limit_headers(resp, rl_headers)
    return resp


@router.post("/logout")
def logout_action():
    resp = RedirectResponse(url="/auth/login", status_code=303)
    for k in ("access_token", "refresh_jwt", "refresh_cookie"):
        resp.delete_cookie(k, path="/")
    return resp

