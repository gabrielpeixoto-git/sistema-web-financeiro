from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.dates import today_in_app
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.budgets import service
from financas_app.app.modules.categories.service import list_categories

router = APIRouter(prefix="/budgets", tags=["budgets"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _table_payload(rows: list[service.BudgetRow]) -> list[dict]:
    table = []
    for r in rows:
        lim, sp, rem, pct = service.format_row_br(r)
        table.append(
            {
                "category": r.category_name,
                "limit": lim,
                "spent": sp,
                "remaining": rem,
                "pct": pct,
                "bar_pct": min(pct, 100),
                "budget_id": r.budget_id,
                "over": r.spent_cents > r.limit_cents,
            }
        )
    return table


def _ym(year: int | None, month: int | None, tz_name: str | None) -> tuple[int, int]:
    t = today_in_app(tz_name)
    y = year if year is not None else t.year
    m = month if month is not None else t.month
    if m < 1 or m > 12:
        m = t.month
    if y < 2000 or y > 2100:
        y = t.year
    return y, m


@router.get("", response_class=HTMLResponse)
def budgets_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
):
    y, m = _ym(year, month, user.timezone)
    rows = service.list_rows(session, user_id=user.id, year=y, month=m)
    table = _table_payload(rows)
    cats = list_categories(session, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "budgets/index.html",
        {
            "request": request,
            "user": user,
            "year": y,
            "month": m,
            "rows": table,
            "categories": cats,
            "prev_y": y - 1 if m == 1 else y,
            "prev_m": 12 if m == 1 else m - 1,
            "next_y": y + 1 if m == 12 else y,
            "next_m": 1 if m == 12 else m + 1,
        },
    )


@router.post("")
def budgets_upsert(
    request: Request,
    category_id: int = Form(...),
    amount: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        service.upsert_budget(
            session,
            user_id=user.id,
            category_id=category_id,
            year=year,
            month=month,
            amount=amount,
        )
    except ValueError:
        y, m = _ym(year, month, user.timezone)
        rows = service.list_rows(session, user_id=user.id, year=y, month=m)
        table = _table_payload(rows)
        return templates.TemplateResponse(
            request,
            "budgets/index.html",
            {
                "request": request,
                "year": y,
                "month": m,
                "rows": table,
                "categories": list_categories(session, user_id=user.id),
                "prev_y": y - 1 if m == 1 else y,
                "prev_m": 12 if m == 1 else m - 1,
                "next_y": y + 1 if m == 12 else y,
                "next_m": 1 if m == 12 else m + 1,
                "error": "Verifique categoria e valor.",
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/budgets?year={year}&month={month}", status_code=303)


@router.post("/{budget_id}/delete")
def budgets_delete(
    budget_id: int,
    year: int = Form(...),
    month: int = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        service.delete_budget(session, user_id=user.id, budget_id=budget_id)
    except ValueError:
        pass
    return RedirectResponse(url=f"/budgets?year={year}&month={month}", status_code=303)
