from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from starlette.responses import HTMLResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.dates import today_in_app
from financas_app.app.common.money import cents_to_brl
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.dashboard import service
from financas_app.app.modules.recurring import service as recurring_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    recurring_service.materialize_due(session, user_id=user.id, until=today_in_app(user.timezone))
    s = service.summary(session, user_id=user.id)
    categories = [(n, cents_to_brl(v)) for n, v in service.by_category(session, user_id=user.id)]

    # Get balance evolution for chart
    evolution = service.balance_evolution(session, user_id=user.id, months=6)
    chart_labels = [e.month_label for e in evolution]
    chart_data = [e.balance_cents for e in evolution]

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "income": cents_to_brl(s.income_cents),
            "expense": cents_to_brl(s.expense_cents),
            "balance": cents_to_brl(s.balance_cents),
            "tx_count": s.tx_count,
            "categories": categories,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
        },
    )

