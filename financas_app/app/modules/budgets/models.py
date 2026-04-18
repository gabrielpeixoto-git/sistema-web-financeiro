from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Budget(SQLModel, table=True):
    __tablename__ = "monthly_budget"
    __table_args__ = (UniqueConstraint("user_id", "category_id", "year", "month", name="uq_monthly_budget_user_cat_ym"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    category_id: int = Field(index=True, foreign_key="category.id")
    year: int = Field(index=True)
    month: int = Field(index=True)
    limit_cents: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
