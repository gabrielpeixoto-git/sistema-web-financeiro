from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    account_id: int = Field(index=True, foreign_key="account.id")
    category_id: int | None = Field(default=None, index=True, foreign_key="category.id")

    # "in" = receita, "out" = despesa (transferência vem depois)
    kind: str = Field(max_length=8)

    # Dinheiro em centavos (inteiro) para evitar problemas de float/decimal em SQLite
    amount_cents: int

    description: str = Field(default="", max_length=200)
    occurred_on: date = Field(index=True)
    transfer_group_id: str | None = Field(default=None, max_length=36, index=True)
    recurring_rule_id: int | None = Field(default=None, index=True, foreign_key="recurringrule.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

