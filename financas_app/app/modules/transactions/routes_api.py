from __future__ import annotations

from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlmodel import Session
from starlette.responses import JSONResponse, Response

from financas_app.app.common.dates import ensure_period_valid
from financas_app.app.common.rate_limit import enforce_rate_limit
from financas_app.app.common.tasks import create_task, get_task
from financas_app.app.deps import get_session
from financas_app.app.modules.auth.deps import get_current_user
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.transactions import import_task, service
from financas_app.app.settings import get_settings

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/export.csv")
def export_csv(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if start is not None and end is not None:
        try:
            ensure_period_valid(start, end)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid period") from None
    content = service.export_csv(session, user_id=user.id, start=start, end=end)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.post("/import")
async def import_csv(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    s = get_settings()
    rl_headers = enforce_rate_limit(
        request,
        scope="transactions.import_csv",
        limit=s.rate_limit_import_per_window,
        window_seconds=s.rate_limit_window_seconds,
    )
    raw = await file.read()
    try:
        content = import_task.read_import_csv_strict(filename=file.filename, raw=raw)
    except import_task.ImportCsvValidationError as e:
        body: dict = {"detail": e.detail, "code": e.code}
        if e.missing_columns:
            body["missing_columns"] = e.missing_columns
        resp = JSONResponse(body, status_code=400)
        for key, value in rl_headers.items():
            resp.headers[key] = value
        return resp

    t = create_task("import_csv")
    background.add_task(
        import_task.run_import_csv_task,
        t.id,
        user_id=user.id,
        content=content,
        db_url=get_settings().database_url,
    )
    resp = JSONResponse({"task_id": t.id, "status": t.status})
    for key, value in rl_headers.items():
        resp.headers[key] = value
    return resp


@router.get("/tasks/{task_id}")
def task_status(task_id: str):
    t = get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "id": t.id,
        "kind": t.kind,
        "status": t.status,
        "detail": t.detail,
        "meta": t.meta,
    }
