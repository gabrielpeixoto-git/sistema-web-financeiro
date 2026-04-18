from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, Request
from sqlmodel import Session, create_engine
from starlette.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from starlette.templating import Jinja2Templates

from financas_app.app.common.tasks import create_task, get_task, set_task
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import require_user_redirect
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.notifications import email_reminders, service
from financas_app.app.settings import get_settings

router = APIRouter(prefix="/notifications", tags=["notifications"])
# Usar caminho absoluto para templates
_templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("", response_class=HTMLResponse)
def notifications_page(
    request: Request,
    kind: str | None = Query(default=None),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    rows = service.list_notifications_filtered(session, user_id=user.id, kind=kind, limit=100)
    kinds = service.list_kinds(session, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "notifications/index.html",
        {"request": request, "user": user, "rows": rows, "kinds": kinds, "kind": kind or ""},
    )


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    service.mark_read(session, user_id=user.id, notification_id=notification_id)
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/read_all")
def mark_all_read(
    kind: str = Form(default=""),
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    service.mark_all_read(session, user_id=user.id)
    url = "/notifications"
    if kind.strip():
        url = f"/notifications?kind={kind.strip()}"
    return RedirectResponse(url=url, status_code=303)


def _run_generate(task_id: str, *, user_id: int, db_url: str) -> None:
    set_task(task_id, status="running")
    try:
        engine = create_engine(db_url, echo=False)
        with Session(engine) as session:
            st = get_settings()
            n = service.generate_for_user(
                session,
                user_id=user_id,
                budget_near_pct=st.notify_budget_near_percent,
                goal_near_pct=st.notify_goal_near_percent,
                dedupe_hours=st.notify_dedupe_hours,
            )
        set_task(task_id, status="done", detail=f"{n} notification(s) created")
    except Exception as e:
        set_task(task_id, status="error", detail=str(e))


@router.post("/generate")
def generate_summary(
    background: BackgroundTasks,
    user: User = Depends(require_user_redirect),
):
    t = create_task("generate_notification")
    background.add_task(_run_generate, t.id, user_id=user.id, db_url=get_settings().database_url)
    return RedirectResponse(url=f"/notifications?task_id={t.id}", status_code=303)


@router.get("/tasks/{task_id}")
def task_status(task_id: str):
    t = get_task(task_id)
    if not t:
        return {"ok": False, "error": "task not found"}
    return {"id": t.id, "kind": t.kind, "status": t.status, "detail": t.detail}


@router.post("/send-email-reminder")
def send_email_reminder(
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    """Send email reminder manually for the current user."""
    result = email_reminders.send_email_reminders_for_user(
        session, user_id=user.id, force=True
    )
    msg = "Lembrete enviado!" if result.get("sent") else f"Não enviado: {result.get('reason', '')}"
    return RedirectResponse(url=f"/notifications?msg={msg}", status_code=303)


# Admin/scheduler endpoint to send reminders to all users
@router.post("/admin/send-all-reminders")
def send_all_reminders(
    background: BackgroundTasks,
    user: User = Depends(require_user_redirect),
    session: Session = Depends(get_session),
):
    """Admin endpoint to trigger email reminders for all users."""
    # Note: In production, add admin check here
    t = create_task("email_reminders_all")

    def _run(task_id: str, db_url: str) -> None:
        set_task(task_id, status="running")
        try:
            engine = create_engine(db_url, echo=False)
            with Session(engine) as s:
                result = email_reminders.run_email_reminders_for_all(s)
            set_task(
                task_id,
                status="done",
                detail=f"Sent to {result['sent_to_users']} users",
            )
        except Exception as e:
            set_task(task_id, status="error", detail=str(e))

    background.add_task(_run, t.id, get_settings().database_url)
    return RedirectResponse(url=f"/notifications?task_id={t.id}", status_code=303)

