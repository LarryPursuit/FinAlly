"""Input validation for tickers, quantities, and trade sides."""

from __future__ import annotations

import re

TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,5}$")
VALID_SIDES = ("buy", "sell")


def validate_ticker(raw: str) -> str:
    """Validate and normalize a ticker symbol.

    Returns the uppercased ticker. Raises ValueError if invalid.
    """
    ticker = raw.strip().upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(
            f"Invalid ticker '{raw}': must be 1-5 characters, [A-Z0-9.-]"
        )
    return ticker


def validate_quantity(qty: float | int) -> int:
    """Validate a trade quantity (v1: integer shares only).

    Returns the quantity as int. Raises ValueError if invalid.
    """
    if not isinstance(qty, (int, float)):
        raise ValueError(f"Invalid quantity: must be a number, got {type(qty).__name__}")
    if qty != int(qty):
        raise ValueError(f"Invalid quantity {qty}: fractional shares not supported in v1")
    qty_int = int(qty)
    if qty_int <= 0:
        raise ValueError(f"Invalid quantity {qty_int}: must be positive")
    return qty_int


def validate_side(side: str) -> str:
    """Validate a trade side ('buy' or 'sell').

    Returns the lowercased side. Raises ValueError if invalid.
    """
    side = side.strip().lower()
    if side not in VALID_SIDES:
        raise ValueError(f"Invalid side '{side}': must be 'buy' or 'sell'")
    return side
