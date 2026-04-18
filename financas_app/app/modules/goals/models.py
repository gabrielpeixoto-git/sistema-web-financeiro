from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class FinancialGoal(SQLModel, table=True):
    __tablename__ = "financial_goal"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    name: str = Field(max_length=120)
    target_cents: int
    saved_cents: int = 0
    due_on: date | None = Field(default=None)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
