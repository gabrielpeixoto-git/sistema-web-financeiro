from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.money import cents_to_brl
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.categories import service

router = APIRouter(prefix="/categories", tags=["categories"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def categories_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    categories = service.list_categories(session, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "categories/index.html",
        {"request": request, "user": user, "categories": categories},
    )


@router.get("/{category_id}", response_class=HTMLResponse)
def category_detail_page(
    request: Request,
    category_id: int,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        stats = service.category_stats(
            session, user_id=user.id, category_id=category_id, start=start, end=end
        )
    except ValueError:
        stats = service.category_stats(session, user_id=user.id, category_id=category_id)
        return templates.TemplateResponse(
            request,
            "categories/detail.html",
            {
                "request": request,
                "user": user,
                "category": stats["category"],
                "income": cents_to_brl(stats["income_cents"]),
                "expense": cents_to_brl(stats["expense_cents"]),
                "net": cents_to_brl(stats["net_cents"]),
                "tx_count": stats["tx_count"],
                "recent": stats["recent"],
                "start": "",
                "end": "",
                "error": "Período inválido: data inicial maior que a final.",
            },
            status_code=400,
        )
    return templates.TemplateResponse(
        request,
        "categories/detail.html",
        {
            "request": request,
            "user": user,
            "category": stats["category"],
            "income": cents_to_brl(stats["income_cents"]),
            "expense": cents_to_brl(stats["expense_cents"]),
            "net": cents_to_brl(stats["net_cents"]),
            "tx_count": stats["tx_count"],
            "recent": stats["recent"],
            "start": start and start.isoformat() or "",
            "end": end and end.isoformat() or "",
            "error": "",
        },
    )


@router.post("")
def categories_create(
    request: Request,
    name: str = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    service.create_category(session, user_id=user.id, name=name)
    return RedirectResponse(url="/categories", status_code=303)

