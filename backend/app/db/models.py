"""Database models as frozen dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class UserProfile:
    """User state including cash balance."""

    id: str
    cash_balance: Decimal
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cash_balance": float(self.cash_balance),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    """A ticker on a user's watchlist."""

    id: str
    user_id: str
    ticker: str
    added_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "added_at": self.added_at,
        }


@dataclass(frozen=True, slots=True)
class Position:
    """A user's holding in a single ticker."""

    id: str
    user_id: str
    ticker: str
    quantity: Decimal
    avg_cost: Decimal
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "quantity": float(self.quantity),
            "avg_cost": float(self.avg_cost),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class Trade:
    """A single executed trade (append-only log)."""

    id: str
    user_id: str
    ticker: str
    side: str
    quantity: Decimal
    price: Decimal
    executed_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": float(self.quantity),
            "price": float(self.price),
            "executed_at": self.executed_at,
        }


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Portfolio value at a point in time."""

    id: str
    user_id: str
    total_value: Decimal
    recorded_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "total_value": float(self.total_value),
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A message in the conversation history."""

    id: str
    user_id: str
    role: str
    content: str
    actions: str | None
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "actions": self.actions,
            "created_at": self.created_at,
        }
