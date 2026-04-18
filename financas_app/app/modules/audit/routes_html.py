from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from starlette.responses import HTMLResponse
from pathlib import Path
from starlette.templating import Jinja2Templates

from financas_app.app.deps import get_session
from financas_app.app.modules.audit import service
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User

router = APIRouter(prefix="/audit", tags=["audit"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def audit_page(
    request: Request,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    rows = service.list_recent(session, user_id=user.id, limit=100)
    payload = [
        {
            "created_at": r.created_at,
            "action": r.action,
            "entity": r.entity,
            "entity_id": r.entity_id,
            "detail": r.detail,
        }
        for r in rows
    ]
    return templates.TemplateResponse(
        request,
        "audit/index.html",
        {"request": request, "user": user, "rows": payload},
    )

