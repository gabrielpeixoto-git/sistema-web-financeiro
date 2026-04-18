from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from financas_app.app.common.rate_limit import enforce_rate_limit


class DummyRequest:
    def __init__(self, host: str = "127.0.0.1", forwarded: str = "") -> None:
        self.client = SimpleNamespace(host=host)
        self.headers = {}
        if forwarded:
            self.headers["x-forwarded-for"] = forwarded


def test_rate_limit_blocks_after_limit(monkeypatch):
    times = iter([1000.0, 1001.0, 1002.0])
    monkeypatch.setattr("financas_app.app.common.rate_limit.time.time", lambda: next(times))
    req = DummyRequest()

    h1 = enforce_rate_limit(req, scope="test.scope", limit=2, window_seconds=60)
    h2 = enforce_rate_limit(req, scope="test.scope", limit=2, window_seconds=60)
    assert h1["X-RateLimit-Remaining"] == "1"
    assert h2["X-RateLimit-Remaining"] == "0"
    assert h1["X-RateLimit-Policy"] == "2;w=60"

    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit(req, scope="test.scope", limit=2, window_seconds=60)
    assert exc.value.status_code == 429
    assert exc.value.headers and "Retry-After" in exc.value.headers
    assert exc.value.headers and exc.value.headers.get("X-RateLimit-Remaining") == "0"
    assert exc.value.headers and exc.value.headers.get("X-RateLimit-Policy") == "2;w=60"


def test_rate_limit_resets_after_window(monkeypatch):
    times = iter([1000.0, 1001.0, 1070.0])
    monkeypatch.setattr("financas_app.app.common.rate_limit.time.time", lambda: next(times))
    req = DummyRequest()

    enforce_rate_limit(req, scope="test.scope.reset", limit=2, window_seconds=60)
    enforce_rate_limit(req, scope="test.scope.reset", limit=2, window_seconds=60)
    h3 = enforce_rate_limit(req, scope="test.scope.reset", limit=2, window_seconds=60)
    assert h3["X-RateLimit-Remaining"] == "1"
