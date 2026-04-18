from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlmodel import SQLModel
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from financas_app.app.common.errors import AuthError
from financas_app.app.db import models as _models  # noqa: F401
from financas_app.app.db.engine import get_engine
from financas_app.app.routes import router as app_router
from financas_app.app.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if get_settings().app_env == "dev":
        SQLModel.metadata.create_all(get_engine())
    else:
        with get_engine().connect():
            pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Finanças App", lifespan=lifespan)

    @app.exception_handler(AuthError)
    def _auth_error(_req, _exc: AuthError):
        return JSONResponse({"ok": False}, status_code=401)

    app.include_router(app_router)
    
    # Usar caminhos absolutos para os diretórios estáticos
    base_dir = Path(__file__).parent
    static_dir = base_dir / "static"
    uploads_dir = base_dir.parent.parent / "uploads"
    
    static_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    return app


app = create_app()