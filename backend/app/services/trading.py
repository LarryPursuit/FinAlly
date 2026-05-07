"""Trade execution service with concurrency control."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from app.db.database import Database
from app.db.seed import DEFAULT_USER_ID
from app.market.cache import PriceCache
from app.services.portfolio import compute_total_value

logger = logging.getLogger(__name__)

# Per-user locks for trade serialization.
# Keyed by (user_id, event_loop_id) to avoid cross-loop reuse in tests.
_trade_locks: dict[tuple[str, int], asyncio.Lock] = {}


def _get_lock(user_id: str) -> asyncio.Lock:
    loop_id = id(asyncio.get_running_loop())
    key = (user_id, loop_id)
    if key not in _trade_locks:
        _trade_locks[key] = asyncio.Lock()
    return _trade_locks[key]


def get_user_lock(user_id: str = DEFAULT_USER_ID) -> asyncio.Lock:
    """Public accessor to the per-user serialization lock used by trade execution.

    Other write paths (e.g., test reset) should acquire this lock to avoid races.
    """
    return _get_lock(user_id)


async def execute_trade(
    db: Database,
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: int,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Execute a market order trade.

    Returns a dict with trade details and updated balances.
    Raises ValueError for validation failures.
    """
    lock = _get_lock(user_id)
    async with lock:
        return await _execute_trade_locked(db, price_cache, ticker, side, quantity, user_id)


async def _execute_trade_locked(
    db: Database,
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: int,
    user_id: str,
) -> dict:
    # Get current price
    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise ValueError(f"No price available for {ticker}")

    price = Decimal(str(current_price))
    qty = Decimal(str(quantity))
    total_cost = price * qty

    user = await db.get_user(user_id)
    if not user:
        raise ValueError("User not found")

    if side == "buy":
        result = await _execute_buy(db, user.cash_balance, ticker, qty, price, total_cost, user_id)
    else:
        result = await _execute_sell(db, user.cash_balance, ticker, qty, price, total_cost, user_id)

    # Record the trade
    trade = await db.record_trade(ticker, side, qty, price, user_id)

    # Record portfolio snapshot after trade
    total_value = await compute_total_value(db, price_cache, user_id)
    await db.record_snapshot(total_value, user_id)

    logger.info(
        "Trade executed: %s %s %s @ %s for user %s",
        side.upper(), quantity, ticker, price, user_id,
    )

    return {
        "success": True,
        "trade": trade.to_dict(),
        "new_cash_balance": round(float(result["new_cash"]), 2),
        "new_position": result["new_position"],
    }


async def _execute_buy(
    db: Database,
    cash_balance: Decimal,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
    total_cost: Decimal,
    user_id: str,
) -> dict:
    if cash_balance < total_cost:
        raise ValueError(
            f"Insufficient cash: need ${float(total_cost):.2f}, have ${float(cash_balance):.2f}"
        )

    new_cash = cash_balance - total_cost
    await db.update_cash_balance(new_cash, user_id)

    # Upsert position with weighted average cost
    existing = await db.get_position(ticker, user_id)
    if existing:
        new_qty = existing.quantity + quantity
        new_avg_cost = (
            (existing.avg_cost * existing.quantity + price * quantity) / new_qty
        )
    else:
        new_qty = quantity
        new_avg_cost = price

    position = await db.upsert_position(ticker, new_qty, new_avg_cost, user_id)

    return {
        "new_cash": new_cash,
        "new_position": {
            "ticker": position.ticker,
            "quantity": float(position.quantity),
            "avg_cost": round(float(position.avg_cost), 2),
        },
    }


async def _execute_sell(
    db: Database,
    cash_balance: Decimal,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
    total_cost: Decimal,
    user_id: str,
) -> dict:
    existing = await db.get_position(ticker, user_id)
    if not existing:
        raise ValueError(f"No position in {ticker} to sell")
    if existing.quantity < quantity:
        raise ValueError(
            f"Insufficient shares: want to sell {float(quantity)}, own {float(existing.quantity)}"
        )

    new_cash = cash_balance + total_cost
    await db.update_cash_balance(new_cash, user_id)

    remaining = existing.quantity - quantity
    if remaining == 0:
        await db.delete_position(ticker, user_id)
        new_position = None
    else:
        position = await db.upsert_position(ticker, remaining, existing.avg_cost, user_id)
        new_position = {
            "ticker": position.ticker,
            "quantity": float(position.quantity),
            "avg_cost": round(float(position.avg_cost), 2),
        }

    return {
        "new_cash": new_cash,
        "new_position": new_position,
    }
