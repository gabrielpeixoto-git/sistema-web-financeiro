from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import HTMLResponse, Response
from pathlib import Path
from starlette.templating import Jinja2Templates
from sqlmodel import Session

from financas_app.app.common.dates import first_day_of_month, today_in_app
from financas_app.app.common.money import cents_to_brl
from financas_app.app.common.pdf import generate_report_pdf
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.accounts.repo import list_accounts
from financas_app.app.modules.categories.repo import list_categories
from financas_app.app.modules.reports import service

router = APIRouter(prefix="/reports", tags=["reports"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def reports_page(
    request: Request,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    today = today_in_app(user.timezone)
    if start is None:
        start = first_day_of_month(today)
    if end is None:
        end = today

    # Load filter options
    accounts = list_accounts(session, user_id=user.id)
    categories = list_categories(session, user_id=user.id)

    try:
        r = service.period_report(session, user_id=user.id, start=start, end=end, account_id=account_id, category_id=category_id)
        by_kind_rows = service.period_by_kind(session, user_id=user.id, start=start, end=end, account_id=account_id, category_id=category_id)
        by_category_rows = service.period_by_category(session, user_id=user.id, start=start, end=end, kind="out", account_id=account_id)
        monthly_rows = service.monthly_trend(session, user_id=user.id, start=start, end=end, account_id=account_id, category_id=category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Período inválido: data inicial maior que a final.") from None

    by_kind = [(k, cents_to_brl(v)) for k, v in by_kind_rows]

    # Prepare chart data
    cat_labels = [name for name, _ in by_category_rows[:6]]
    cat_values = [amount for _, amount in by_category_rows[:6]]

    trend_labels = [m.replace("-", "/") for m, _, _ in monthly_rows]
    trend_income = [inc for _, inc, _ in monthly_rows]
    trend_expense = [exp for _, _, exp in monthly_rows]

    return templates.TemplateResponse(
        request,
        "reports/index.html",
        {
            "request": request,
            "user": user,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "account_id": account_id,
            "category_id": category_id,
            "accounts": accounts,
            "categories": categories,
            "income": cents_to_brl(r.income_cents),
            "expense": cents_to_brl(r.expense_cents),
            "net": cents_to_brl(r.net_cents),
            "count": r.count,
            "by_kind": by_kind,
            "cat_labels": cat_labels,
            "cat_values": cat_values,
            "trend_labels": trend_labels,
            "trend_income": trend_income,
            "trend_expense": trend_expense,
        },
    )


@router.get("/export.pdf")
def export_pdf(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    """Export reports as PDF."""
    today = today_in_app(user.timezone)
    if start is None:
        start = first_day_of_month(today)
    if end is None:
        end = today

    try:
        r = service.period_report(session, user_id=user.id, start=start, end=end, account_id=account_id, category_id=category_id)
        by_category_rows = service.period_by_category(session, user_id=user.id, start=start, end=end, kind="out", account_id=account_id)
        monthly_rows = service.monthly_trend(session, user_id=user.id, start=start, end=end, account_id=account_id, category_id=category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Período inválido") from None

    pdf_bytes = generate_report_pdf(
        start=start,
        end=end,
        income_cents=r.income_cents,
        expense_cents=r.expense_cents,
        net_cents=r.net_cents,
        count=r.count,
        by_category=by_category_rows,
        monthly_rows=monthly_rows,
    )

    filename = f"relatorio_{start.isoformat()}_{end.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

