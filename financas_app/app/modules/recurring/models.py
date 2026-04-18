from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RecurringRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    account_id: int = Field(index=True, foreign_key="account.id")
    category_id: int | None = Field(default=None, index=True, foreign_key="category.id")
    kind: str = Field(max_length=8)
    amount_cents: int
    description: str = Field(default="", max_length=200)
    frequency: str = Field(max_length=16)
    next_due: date = Field(index=True)
    end_on: date | None = None
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
