from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.dates import today_in_app
from financas_app.app.common.money import cents_to_brl
from financas_app.app.deps import get_session
from financas_app.app.modules.accounts.service import list_accounts
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.categories.service import list_categories
from financas_app.app.modules.recurring import repo
from financas_app.app.modules.recurring import service

router = APIRouter(prefix="/recurring", tags=["recurring"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def recurring_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    today = today_in_app(user.timezone)
    n = service.materialize_due(session, user_id=user.id, until=today)
    accounts = list_accounts(session, user_id=user.id)
    categories = list_categories(session, user_id=user.id)
    rules = repo.list_active(session, user.id)
    rows = [
        {
            "id": r.id,
            "next_due": r.next_due,
            "frequency": r.frequency,
            "kind": r.kind,
            "amount": cents_to_brl(r.amount_cents),
            "description": r.description,
            "end_on": r.end_on,
        }
        for r in rules
    ]
    return templates.TemplateResponse(
        request,
        "recurring/index.html",
        {
            "request": request,
            "user": user,
            "rules": rows,
            "accounts": accounts,
            "categories": categories,
            "today": today.isoformat(),
            "materialized": n,
        },
    )


@router.post("")
def recurring_create(
    request: Request,
    kind: str = Form(...),
    account_id: int = Form(...),
    amount: str = Form(...),
    frequency: str = Form(...),
    start_on: date = Form(...),
    end_on_raw: str = Form(default=""),
    category_id_raw: str = Form(default=""),
    description: str = Form(default=""),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    end_on = date.fromisoformat(end_on_raw.strip()) if end_on_raw.strip() else None
    category_id = int(category_id_raw) if category_id_raw.strip().isdigit() else None
    try:
        service.create_rule(
            session,
            user_id=user.id,
            account_id=account_id,
            kind=kind,
            amount=amount,
            frequency=frequency,
            start_on=start_on,
            end_on=end_on,
            category_id=category_id,
            description=description,
        )
    except ValueError:
        today = today_in_app(user.timezone)
        n = service.materialize_due(session, user_id=user.id, until=today)
        rules = repo.list_active(session, user.id)
        rows = [
            {
                "id": r.id,
                "next_due": r.next_due,
                "frequency": r.frequency,
                "kind": r.kind,
                "amount": cents_to_brl(r.amount_cents),
                "description": r.description,
                "end_on": r.end_on,
            }
            for r in rules
        ]
        return templates.TemplateResponse(
            request,
            "recurring/index.html",
            {
                "request": request,
                "error": "Dados inválidos. Verifique conta, categoria, valor e período.",
                "rules": rows,
                "accounts": list_accounts(session, user_id=user.id),
                "categories": list_categories(session, user_id=user.id),
                "today": today.isoformat(),
                "materialized": n,
            },
            status_code=400,
        )
    return RedirectResponse(url="/recurring", status_code=303)


@router.post("/{rule_id}/off")
def recurring_off(
    rule_id: int,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        service.deactivate(session, user_id=user.id, rule_id=rule_id)
    except ValueError:
        pass
    return RedirectResponse(url="/recurring", status_code=303)
