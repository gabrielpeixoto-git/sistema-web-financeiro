from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlmodel import Session
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates

from financas_app.app.common.dates import today_in_app
from financas_app.app.common.money import cents_to_brl
from financas_app.app.common.rate_limit import enforce_rate_limit
from financas_app.app.common.tasks import create_task, get_task, set_task
from financas_app.app.deps import get_session
from financas_app.app.modules.accounts.service import list_accounts
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.categories.service import list_categories
from financas_app.app.modules.recurring import service as recurring_service
from financas_app.app.modules.transactions import import_task, service
from financas_app.app.settings import get_settings

router = APIRouter(prefix="/transactions", tags=["transactions"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

_SKIP_REASON_LABELS = {
    "invalid_kind": "Tipo de lançamento inválido",
    "account_not_found": "Conta não encontrada",
    "category_not_found": "Categoria não encontrada",
    "invalid_amount": "Valor inválido",
    "duplicate": "Duplicado (já existia)",
    "row_error": "Erro na linha",
}

_IMPORT_PREVIEW_LIMIT = 10


def _render_tx_page(
    request: Request,
    *,
    user: User,
    session: Session,
    error: str = "",
    transfer: dict | None = None,
):
    today = today_in_app(user.timezone)
    recurring_service.materialize_due(session, user_id=user.id, until=today)
    txs = service.list_transactions(session, user_id=user.id, limit=50)
    accounts = list_accounts(session, user_id=user.id)
    categories = list_categories(session, user_id=user.id)
    total = cents_to_brl(service.balance_total(session, user_id=user.id))
    tx_rows = [
        {
            "occurred_on": t.occurred_on,
            "kind": t.kind,
            "description": t.description,
            "amount": cents_to_brl(t.amount_cents),
        }
        for t in txs
    ]
    return templates.TemplateResponse(
        request,
        "transactions/index.html",
        {
            "request": request,
            "user": user,
            "txs": tx_rows,
            "accounts": accounts,
            "categories": categories,
            "total": total,
            "today": today.isoformat(),
            "error": error,
            "transfer": transfer or {},
        },
    )


@router.get("", response_class=HTMLResponse)
def tx_page(
    request: Request,
    user: User = Depends(require_user_redirect),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
):
    return _render_tx_page(request, user=user, session=session)


@router.get("/new", response_class=HTMLResponse)
def tx_new_page(
    request: Request,
    user: User = Depends(require_user_redirect),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
):
    """Renderiza página dedicada para criar nova transação."""
    today = today_in_app(user.timezone)
    accounts = list_accounts(session, user_id=user.id)
    categories = list_categories(session, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "transactions/new.html",
        {
            "request": request,
            "user": user,
            "accounts": accounts,
            "categories": categories,
            "today": today.isoformat(),
        },
    )


@router.get("/import", response_class=HTMLResponse)
def tx_import_page(
    request: Request,
    user: User = Depends(require_user_redirect),  # noqa: B008
):
    """Renderiza página para importar transações via CSV."""
    return templates.TemplateResponse(
        request,
        "transactions/import.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/")
def tx_create(
    kind: str = Form(...),  # noqa: B008
    account_id: int = Form(...),  # noqa: B008
    amount: str = Form(...),  # noqa: B008
    occurred_on: date = Form(...),  # noqa: B008
    category_id: int | None = Form(default=None),  # noqa: B008
    description: str = Form(default=""),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
):
    service.create_transaction(
        session,
        user_id=user.id,
        account_id=account_id,
        kind=kind,
        amount=amount,
        occurred_on=occurred_on,
        category_id=category_id,
        description=description,
    )
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("")
def tx_create_no_slash(
    kind: str = Form(...),  # noqa: B008
    account_id: int = Form(...),  # noqa: B008
    amount: str = Form(...),  # noqa: B008
    occurred_on: date = Form(...),  # noqa: B008
    category_id: int | None = Form(default=None),  # noqa: B008
    description: str = Form(default=""),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
):
    service.create_transaction(
        session,
        user_id=user.id,
        account_id=account_id,
        kind=kind,
        amount=amount,
        occurred_on=occurred_on,
        category_id=category_id,
        description=description,
    )
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/transfer")
def tx_transfer(
    request: Request,
    from_account_id: int = Form(...),  # noqa: B008
    to_account_id: int = Form(...),  # noqa: B008
    amount: str = Form(...),  # noqa: B008
    occurred_on: date = Form(...),  # noqa: B008
    description: str = Form(default=""),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
):
    try:
        service.create_transfer(
            session,
            user_id=user.id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            occurred_on=occurred_on,
            description=description,
        )
    except ValueError as e:
        msg = {
            "same account": "A conta de origem e a conta de destino devem ser diferentes.",
            "invalid account": "Conta de origem ou destino inválida.",
            "amount must be > 0": "Informe um valor de transferência maior que zero.",
            "insufficient balance": "Saldo insuficiente na conta de origem para esta transferência.",
        }.get(str(e), "Não foi possível realizar a transferência. Revise os dados e tente novamente.")
        transfer = {
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "description": description,
        }
        return _render_tx_page(request, user=user, session=session, error=msg, transfer=transfer)
    return RedirectResponse(url="/transactions", status_code=303)


def _skip_reason_rows(meta: dict | None) -> list[tuple[str, int]]:
    sr = (meta or {}).get("skip_reasons") or {}
    out: list[tuple[str, int]] = []
    for k, v in sorted(sr.items()):
        if v:
            out.append((_SKIP_REASON_LABELS.get(k, k), int(v)))
    return out


def _skip_sample_rows(meta: dict | None) -> list[tuple[int, str]]:
    raw = (meta or {}).get("skip_samples") or []
    out: list[tuple[int, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ln = item.get("line")
        reason = str(item.get("reason") or "")
        if ln is None:
            continue
        label = _SKIP_REASON_LABELS.get(reason, reason)
        out.append((int(ln), label))
    return out


@router.post("/import/preview", response_class=HTMLResponse)
async def import_csv_preview_html(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
):
    s = get_settings()
    enforce_rate_limit(
        request,
        scope="transactions.import_csv",
        limit=s.rate_limit_import_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    raw = await file.read()
    try:
        content = import_task.read_import_csv_strict(filename=file.filename, raw=raw)
    except import_task.ImportCsvValidationError as e:
        return templates.TemplateResponse(
            request,
            "transactions/partials/import_error.html",
            {
                "request": request,
                "detail": e.detail,
                "code": e.code,
                "missing_columns": e.missing_columns,
            },
            status_code=200,
        )

    reader = csv.DictReader(io.StringIO(content))
    preview_rows: list[dict[str, str]] = []
    for _ in range(_IMPORT_PREVIEW_LIMIT):
        row = next(reader, None)
        if not row:
            break
        preview_rows.append(
            {
                "date": (row.get("date") or "").strip(),
                "kind": (row.get("kind") or "").strip(),
                "account_name": (row.get("account_name") or "").strip(),
                "category_name": (row.get("category_name") or "").strip(),
                "amount": (row.get("amount") or "").strip(),
                "description": (row.get("description") or "").strip(),
            }
        )

    t = create_task("import_csv_preview")
    set_task(t.id, status="pending", meta={"user_id": user.id, "content": content})
    return templates.TemplateResponse(
        request,
        "transactions/partials/import_preview.html",
        {"request": request, "task_id": t.id, "rows": preview_rows, "limit": _IMPORT_PREVIEW_LIMIT},
    )


@router.post("/import/confirm", response_class=HTMLResponse)
def import_csv_confirm_html(
    request: Request,
    background: BackgroundTasks,
    task_id: str = Form(...),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
):
    t = get_task(task_id)
    meta = (t.meta or {}) if t else {}
    content = meta.get("content") if isinstance(meta, dict) else None
    owner = meta.get("user_id") if isinstance(meta, dict) else None
    if not t or not isinstance(content, str) or not owner or int(owner) != user.id:
        return templates.TemplateResponse(
            request,
            "transactions/partials/import_error.html",
            {
                "request": request,
                "detail": "Pré-visualização expirada. Envie o arquivo novamente.",
                "code": "preview_expired",
                "missing_columns": [],
            },
            status_code=200,
        )
    s = get_settings()
    background.add_task(
        import_task.run_import_csv_task,
        t.id,
        user_id=user.id,
        content=content,
        db_url=s.database_url,
    )
    return templates.TemplateResponse(
        request,
        "transactions/partials/import_status.html",
        {
            "request": request,
            "task_id": t.id,
            "poll": True,
            "status": "pending",
            "detail": "",
            "created": None,
            "skipped": None,
            "skip_rows": [],
            "skip_sample_rows": [],
            "error_detail": "",
        },
    )


@router.post("/import", response_class=HTMLResponse)
async def import_csv_html(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    user: User = Depends(require_user_redirect),  # noqa: B008
):
    s = get_settings()
    enforce_rate_limit(
        request,
        scope="transactions.import_csv",
        limit=s.rate_limit_import_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    raw = await file.read()
    try:
        content = import_task.read_import_csv_strict(filename=file.filename, raw=raw)
    except import_task.ImportCsvValidationError as e:
        return templates.TemplateResponse(
            request,
            "transactions/partials/import_error.html",
            {
                "request": request,
                "detail": e.detail,
                "code": e.code,
                "missing_columns": e.missing_columns,
            },
            status_code=200,
        )
    t = create_task("import_csv")
    background.add_task(
        import_task.run_import_csv_task,
        t.id,
        user_id=user.id,
        content=content,
        db_url=s.database_url,
    )
    return templates.TemplateResponse(
        request,
        "transactions/partials/import_status.html",
        {
            "request": request,
            "task_id": t.id,
            "poll": True,
            "status": t.status,
            "detail": "",
            "created": None,
            "skipped": None,
            "skip_rows": [],
            "skip_sample_rows": [],
            "error_detail": "",
        },
    )


@router.get("/import-status/{task_id}", response_class=HTMLResponse)
def import_csv_status(
    request: Request,
    task_id: str,
    user: User = Depends(require_user_redirect),  # noqa: B008
):
    t = get_task(task_id)
    if not t:
        return templates.TemplateResponse(
            request,
            "transactions/partials/import_status.html",
            {
                "request": request,
                "task_id": task_id,
                "poll": False,
                "status": "missing",
                "detail": "",
                "created": None,
                "skipped": None,
                "skip_rows": [],
                "skip_sample_rows": [],
                "error_detail": "Tarefa não encontrada ou expirada.",
            },
        )
    poll = t.status in ("pending", "running")
    meta = t.meta or {}
    m = meta if isinstance(meta, dict) else {}
    return templates.TemplateResponse(
        request,
        "transactions/partials/import_status.html",
        {
            "request": request,
            "task_id": task_id,
            "poll": poll,
            "status": t.status,
            "detail": t.detail,
            "created": meta.get("created"),
            "skipped": meta.get("skipped"),
            "skip_rows": _skip_reason_rows(m),
            "skip_sample_rows": _skip_sample_rows(m),
            "error_detail": t.detail if t.status == "error" else "",
        },
    )

