from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.dates import today_in_app
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.goals import service

router = APIRouter(prefix="/goals", tags=["goals"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _rows_payload(session: Session, user_id: int) -> list[dict]:
    out = []
    for r in service.list_rows(session, user_id=user_id):
        out.append(service.format_row(r))
    return out


@router.get("", response_class=HTMLResponse)
def goals_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    rows = _rows_payload(session, user.id)
    return templates.TemplateResponse(
        request,
        "goals/index.html",
        {"request": request, "user": user, "rows": rows, "today": today_in_app(user.timezone).isoformat()},
    )


@router.post("")
def goals_create(
    request: Request,
    name: str = Form(...),
    target: str = Form(...),
    due_on_raw: str = Form(default=""),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    due = date.fromisoformat(due_on_raw.strip()) if due_on_raw.strip() else None
    try:
        service.create_goal(session, user_id=user.id, name=name, target=target, due_on=due)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "goals/index.html",
            {
                "request": request,
                "rows": _rows_payload(session, user.id),
                "today": today_in_app(user.timezone).isoformat(),
                "error": "Verifique nome e valor alvo.",
            },
            status_code=400,
        )
    return RedirectResponse(url="/goals", status_code=303)


@router.post("/{goal_id}/progress")
def goals_add_progress(
    request: Request,
    goal_id: int,
    amount: str = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        service.add_progress(session, user_id=user.id, goal_id=goal_id, amount=amount)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "goals/index.html",
            {
                "request": request,
                "rows": _rows_payload(session, user.id),
                "today": today_in_app(user.timezone).isoformat(),
                "error": "Valor inválido ou meta inexistente.",
            },
            status_code=400,
        )
    return RedirectResponse(url="/goals", status_code=303)


@router.post("/{goal_id}/off")
def goals_off(
    goal_id: int,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        service.deactivate(session, user_id=user.id, goal_id=goal_id)
    except ValueError:
        pass
    return RedirectResponse(url="/goals", status_code=303)
