from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, File
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from sqlmodel import Session, select
import os
import uuid
from pathlib import Path

from financas_app.app.common.dates import validate_timezone
from financas_app.app.deps import get_session
from financas_app.app.modules.accounts.routes_html import router as accounts_router
from financas_app.app.modules.auth.deps import (
    get_current_user,
    get_current_user_optional,
    require_user_redirect,
)
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.auth.routes_api import router as auth_api_router
from financas_app.app.modules.auth.routes_html import router as auth_html_router
from financas_app.app.modules.categories.routes_html import router as categories_router
from financas_app.app.modules.dashboard.routes_html import router as dashboard_router
from financas_app.app.modules.reports.routes_html import router as reports_router
from financas_app.app.modules.transactions.routes_html import router as transactions_router
from financas_app.app.modules.transactions.routes_api import router as transactions_api_router
from financas_app.app.modules.notifications.routes_html import router as notifications_router
from financas_app.app.modules.audit.routes_html import router as audit_router
from financas_app.app.modules.recurring.routes_html import router as recurring_router
from financas_app.app.modules.budgets.routes_html import router as budgets_router
from financas_app.app.modules.goals.routes_html import router as goals_router

router = APIRouter()
# Usar caminho absoluto para os templates
_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))
router.include_router(auth_html_router)
router.include_router(auth_api_router)
router.include_router(accounts_router)
router.include_router(categories_router)
router.include_router(transactions_router)
router.include_router(transactions_api_router)
router.include_router(dashboard_router)
router.include_router(reports_router)
router.include_router(notifications_router)
router.include_router(audit_router)
router.include_router(recurring_router)
router.include_router(budgets_router)
router.include_router(goals_router)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "home.html", {"request": request, "user": user})


@router.get("/health", response_class=HTMLResponse)
def health():
    return "<span class='text-emerald-700 font-medium'>ok</span>"


@router.get("/account", response_class=HTMLResponse)
def account_page(
    request: Request,
    msg: str | None = Query(default=None),
    user: User = Depends(require_user_redirect),
):
    return templates.TemplateResponse(
        request, "account/index.html", {"request": request, "user": user, "msg": msg or ""}
    )


@router.post("/account/timezone")
def account_timezone(
    timezone: str = Form(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    try:
        tz = validate_timezone(timezone.strip())
    except ValueError:
        return RedirectResponse(url="/account?msg=Timezone%20inv%C3%A1lido.", status_code=303)
    user.timezone = tz
    session.add(user)
    session.commit()
    return RedirectResponse(url="/account?msg=Timezone%20atualizado.", status_code=303)


@router.post("/account/upload-profile")
def upload_profile_image(
    file: UploadFile = File(...),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    # Validar tipo de arquivo
    if not file.content_type.startswith("image/"):
        return RedirectResponse(url="/account?msg=Apenas%20imagens%20s%C3%A3o%20permitidas.", status_code=303)
    
    # Criar pasta uploads se não existir
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    # Gerar nome de arquivo único
    file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = uploads_dir / unique_filename
    
    # Salvar arquivo
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Remover foto antiga se existir
    if user.profile_image_url:
        old_file_path = Path(user.profile_image_url.lstrip("/"))
        if old_file_path.exists():
            old_file_path.unlink()
    
    # Atualizar URL no banco
    user.profile_image_url = f"/uploads/{unique_filename}"
    session.add(user)
    session.commit()
    
    return RedirectResponse(url="/account?msg=Foto%20de%20perfil%20atualizada.", status_code=303)


@router.post("/account/remove-profile")
def remove_profile_image(
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    # Remover arquivo se existir
    if user.profile_image_url:
        file_path = Path(user.profile_image_url.lstrip("/"))
        if file_path.exists():
            file_path.unlink()
    
    # Limpar URL no banco
    user.profile_image_url = None
    session.add(user)
    session.commit()
    
    return RedirectResponse(url="/account?msg=Foto%20de%20perfil%20removida.", status_code=303)


@router.post("/account/email-reminders")
def update_email_reminders(
    enabled: str = Form(default=""),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    user.email_reminders_enabled = enabled == "true"
    session.add(user)
    session.commit()
    status = "ativados" if user.email_reminders_enabled else "desativados"
    return RedirectResponse(url=f"/account?msg=Lembretes%20{status}.", status_code=303)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "profile_image_url": user.profile_image_url}


@router.get("/health-check")
def health_check(session: Session = Depends(get_session)):
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        session.exec(select(1))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "database": str(e)},
            status_code=503
        )