from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.deps import get_session
from financas_app.app.modules.accounts import service
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User

router = APIRouter(prefix="/accounts", tags=["accounts"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def accounts_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    accounts = service.list_accounts(session, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "accounts/index.html",
        {"request": request, "user": user, "accounts": accounts},
    )


@router.post("/")
def create_account(
    request: Request,
    name: str = Form(...),
    kind: str = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    # O modelo Account usa 'currency', não 'kind'
    currency = "BRL"
    account = service.create_account(session, name=name, currency=currency, user_id=user.id)
    return RedirectResponse("/accounts", status_code=303)
