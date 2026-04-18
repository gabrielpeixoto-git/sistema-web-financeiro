from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request

_LOCK = threading.Lock()
_HITS: dict[str, deque[float]] = {}


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> dict[str, str]:
    now = time.time()
    key = f"{scope}:{client_key(request)}"
    cutoff = now - window_seconds

    with _LOCK:
        q = _HITS.setdefault(key, deque())
        while q and q[0] <= cutoff:
            q.popleft()
        policy = f"{limit};w={window_seconds}"
        if len(q) >= limit:
            retry_after = max(1, int(window_seconds - (now - q[0])))
            reset_in = retry_after
            raise HTTPException(
                status_code=429,
                detail="too many requests",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "X-RateLimit-Policy": policy,
                },
            )
        q.append(now)
        remaining = max(0, limit - len(q))
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(window_seconds),
        "X-RateLimit-Policy": policy,
    }
