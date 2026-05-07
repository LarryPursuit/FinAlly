"""Health check endpoint."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter

from app.db.database import Database
from app.market.interface import MarketDataSource

logger = logging.getLogger(__name__)


def create_health_router(
    db: Database,
    market_data_source: MarketDataSource,
    snapshot_task: asyncio.Task | None = None,
) -> APIRouter:
    """Create the health check router."""
    router = APIRouter(prefix="/api", tags=["system"])

    @router.get("/health")
    async def health_check() -> dict:
        snapshot_status = "stopped"
        if snapshot_task is not None and not snapshot_task.done():
            snapshot_status = "running"
        return {
            "status": "healthy",
            "database": "connected" if db.is_connected else "disconnected",
            "market_data": "running" if market_data_source.get_tickers() else "stopped",
            "snapshot_task": snapshot_status,
        }

    return router
