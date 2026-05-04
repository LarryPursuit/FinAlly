"""Health check endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.db.database import Database
from app.market.interface import MarketDataSource

logger = logging.getLogger(__name__)


def create_health_router(db: Database, market_data_source: MarketDataSource) -> APIRouter:
    """Create the health check router."""
    router = APIRouter(prefix="/api", tags=["system"])

    @router.get("/health")
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "database": "connected" if db.is_connected else "disconnected",
            "market_data": "running" if market_data_source.get_tickers() else "stopped",
        }

    return router
