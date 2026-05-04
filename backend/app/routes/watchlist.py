"""Watchlist API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.database import Database
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.validation import validate_ticker

logger = logging.getLogger(__name__)


class AddTickerRequest(BaseModel):
    ticker: str


def create_watchlist_router(
    db: Database,
    price_cache: PriceCache,
    market_data_source: MarketDataSource,
) -> APIRouter:
    """Create the watchlist router with injected dependencies."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    async def get_watchlist() -> dict:
        """Current watchlist tickers with latest prices."""
        entries = await db.get_watchlist()
        tickers = []
        for entry in entries:
            price_update = price_cache.get(entry.ticker)
            if price_update:
                tickers.append({
                    "ticker": entry.ticker,
                    "current_price": price_update.price,
                    "previous_price": price_update.previous_price,
                    "change_pct": price_update.change_percent,
                    "added_at": entry.added_at,
                })
            else:
                tickers.append({
                    "ticker": entry.ticker,
                    "current_price": None,
                    "previous_price": None,
                    "change_pct": 0.0,
                    "added_at": entry.added_at,
                })
        return {"tickers": tickers}

    @router.post("")
    async def add_ticker(request: AddTickerRequest) -> JSONResponse:
        """Add a ticker to the watchlist."""
        try:
            ticker = validate_ticker(request.ticker)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid ticker: {request.ticker}", "code": "INVALID_TICKER"},
            )

        try:
            entry = await db.add_to_watchlist(ticker)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Ticker {ticker} already in watchlist",
                    "code": "INVALID_TICKER",
                },
            )

        # Register with market data source so prices start flowing
        await market_data_source.add_ticker(ticker)

        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "ticker": ticker,
                "added_at": entry.added_at,
            },
        )

    @router.delete("/{ticker}")
    async def remove_ticker(ticker: str) -> JSONResponse:
        """Remove a ticker from the watchlist."""
        try:
            validated = validate_ticker(ticker)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid ticker: {ticker}", "code": "INVALID_TICKER"},
            )

        removed = await db.remove_from_watchlist(validated)
        if not removed:
            return JSONResponse(
                status_code=404,
                content={"error": f"Ticker {validated} not in watchlist", "code": "TICKER_NOT_FOUND"},
            )

        await market_data_source.remove_ticker(validated)

        return JSONResponse(status_code=200, content={"success": True, "ticker": validated})

    return router
