from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    name: str
    currency: str = Field(default="BRL", max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

