"""Portfolio valuation service."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.db.database import Database
from app.db.seed import DEFAULT_USER_ID
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)


async def compute_total_value(
    db: Database, price_cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> Decimal:
    """Compute total portfolio value: cash + sum(position_quantity * current_price)."""
    user = await db.get_user(user_id)
    if not user:
        return Decimal("0")

    total = user.cash_balance
    positions = await db.get_positions(user_id)
    for pos in positions:
        current_price = price_cache.get_price(pos.ticker)
        if current_price is not None:
            total += pos.quantity * Decimal(str(current_price))
    return total


async def get_portfolio_summary(
    db: Database, price_cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> dict:
    """Build a complete portfolio summary with positions and P&L."""
    user = await db.get_user(user_id)
    if not user:
        return {"error": "User not found", "code": "INTERNAL_ERROR"}

    positions = await db.get_positions(user_id)
    total_value = user.cash_balance
    position_list = []

    for pos in positions:
        current_price = price_cache.get_price(pos.ticker)
        if current_price is None:
            current_price_dec = pos.avg_cost
        else:
            current_price_dec = Decimal(str(current_price))

        market_value = pos.quantity * current_price_dec
        cost_basis = pos.quantity * pos.avg_cost
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (
            float(unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0
        )

        total_value += market_value

        position_list.append({
            "ticker": pos.ticker,
            "quantity": float(pos.quantity),
            "avg_cost": round(float(pos.avg_cost), 2),
            "current_price": round(float(current_price_dec), 2),
            "market_value": round(float(market_value), 2),
            "unrealized_pnl": round(float(unrealized_pnl), 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
        })

    return {
        "cash_balance": round(float(user.cash_balance), 2),
        "total_value": round(float(total_value), 2),
        "positions": position_list,
    }
