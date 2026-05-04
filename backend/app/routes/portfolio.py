"""Portfolio API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.database import Database
from app.market.cache import PriceCache
from app.services.portfolio import get_portfolio_summary
from app.services.trading import execute_trade
from app.validation import validate_quantity, validate_side, validate_ticker

logger = logging.getLogger(__name__)


class TradeRequest(BaseModel):
    ticker: str
    quantity: float | int
    side: str


def create_portfolio_router(db: Database, price_cache: PriceCache) -> APIRouter:
    """Create the portfolio router with injected dependencies."""
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def get_portfolio() -> dict:
        """Current positions, cash balance, total value, unrealized P&L."""
        return await get_portfolio_summary(db, price_cache)

    @router.post("/trade")
    async def post_trade(request: TradeRequest) -> JSONResponse:
        """Execute a market order trade."""
        try:
            ticker = validate_ticker(request.ticker)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid ticker: {request.ticker}", "code": "INVALID_TICKER"},
            )

        try:
            quantity = validate_quantity(request.quantity)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": str(request.quantity), "code": "INVALID_QUANTITY"},
            )

        try:
            side = validate_side(request.side)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid side: {request.side}", "code": "INVALID_SIDE"},
            )

        try:
            result = await execute_trade(db, price_cache, ticker, side, quantity)
        except ValueError as e:
            msg = str(e)
            if "Insufficient cash" in msg:
                code = "INSUFFICIENT_CASH"
            elif "Insufficient shares" in msg or "No position" in msg:
                code = "INSUFFICIENT_SHARES"
            elif "No price" in msg:
                code = "INVALID_TICKER"
            else:
                code = "INTERNAL_ERROR"
            return JSONResponse(
                status_code=400,
                content={"error": msg, "code": code},
            )

        return JSONResponse(status_code=200, content=result)

    @router.get("/history")
    async def get_history() -> dict:
        """Portfolio value snapshots over time."""
        snapshots = await db.get_snapshots()
        return {
            "snapshots": [
                {
                    "total_value": round(float(s.total_value), 2),
                    "recorded_at": s.recorded_at,
                }
                for s in snapshots
            ]
        }

    return router
