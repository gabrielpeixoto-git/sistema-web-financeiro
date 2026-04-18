from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TaskState:
    id: str
    kind: str
    status: str = "pending"  # pending | running | done | error
    detail: str = ""
    meta: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_LOCK = threading.Lock()
_TASKS: dict[str, TaskState] = {}


def create_task(kind: str) -> TaskState:
    t = TaskState(id=uuid.uuid4().hex, kind=kind)
    with _LOCK:
        _TASKS[t.id] = t
    return t


def set_task(task_id: str, *, status: str, detail: str = "", meta: dict | None = None) -> None:
    with _LOCK:
        t = _TASKS.get(task_id)
        if not t:
            return
        t.status = status
        t.detail = detail
        if meta is not None:
            t.meta = meta
        t.updated_at = datetime.now(UTC)


def get_task(task_id: str) -> TaskState | None:
    with _LOCK:
        return _TASKS.get(task_id)

