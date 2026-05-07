"""Test-only administrative routes.

These endpoints are GUARDED by the ALLOW_TEST_RESET environment variable and
return 403 unless explicitly enabled. Never set ALLOW_TEST_RESET in production.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.database import Database
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.services.trading import get_user_lock

logger = logging.getLogger(__name__)

ALLOW_TEST_RESET_ENV = "ALLOW_TEST_RESET"


def _reset_enabled() -> bool:
    return os.getenv(ALLOW_TEST_RESET_ENV, "").lower() == "true"


def create_test_admin_router(
    db: Database,
    price_cache: PriceCache,
    market_data_source: MarketDataSource,
) -> APIRouter:
    """Create the test-admin router with injected dependencies."""
    router = APIRouter(prefix="/api/test", tags=["test"])

    @router.post("/reset")
    async def reset_state() -> JSONResponse:
        """Wipe and reseed the database. Refused unless ALLOW_TEST_RESET=true."""
        if not _reset_enabled():
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Test reset endpoint is disabled",
                    "code": "FORBIDDEN",
                },
            )

        lock = get_user_lock()
        async with lock:
            await db.reset_to_seed()
            tickers = await db.get_watchlist_tickers()
            # Re-register seed tickers with the running market data source.
            # add_ticker is idempotent and avoids re-starting the loop task.
            for ticker in tickers:
                await market_data_source.add_ticker(ticker)

        logger.info("Test reset completed: %d tickers seeded", len(tickers))
        return JSONResponse(status_code=200, content={"ok": True})

    return router
