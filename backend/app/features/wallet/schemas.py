"""Wallet DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WalletOut(BaseModel):
    balance_amount: int
    currency: str = "INR"


class TxnOut(BaseModel):
    id: uuid.UUID
    direction: str
    amount: int
    balance_after: int
    source: str
    note: str | None
    created_at: datetime


class AdjustIn(BaseModel):
    amount: int = Field(description="Positive = credit, negative = debit")
    note: str | None = Field(default=None, max_length=255)
