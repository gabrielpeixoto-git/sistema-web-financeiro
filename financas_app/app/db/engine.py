from __future__ import annotations

from sqlmodel import create_engine

from financas_app.app.settings import get_settings

_CACHE: dict[str, object] = {}


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def get_engine():
    url = get_settings().database_url
    eng = _CACHE.get(url)
    if eng is None:
        eng = create_engine(url, echo=False, **_engine_kwargs(url))
        _CACHE[url] = eng
    return eng