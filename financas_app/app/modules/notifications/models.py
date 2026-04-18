from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    kind: str = Field(default="info", max_length=32, index=True)
    message: str = Field(max_length=400)
    read_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

