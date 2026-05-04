"""Background tasks for portfolio snapshots and cleanup."""

from __future__ import annotations

import asyncio
import logging

from app.db.database import Database
from app.market.cache import PriceCache
from app.services.portfolio import compute_total_value

logger = logging.getLogger(__name__)


async def snapshot_loop(
    db: Database,
    price_cache: PriceCache,
    interval: float = 30.0,
) -> None:
    """Record portfolio value snapshot every `interval` seconds.

    Runs until cancelled. Handles exceptions without crashing.
    """
    logger.info("Snapshot task started (interval=%ss)", interval)
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                total_value = await compute_total_value(db, price_cache)
                await db.record_snapshot(total_value)
                logger.debug("Snapshot recorded: $%.2f", total_value)
            except Exception:
                logger.exception("Error recording snapshot")
    except asyncio.CancelledError:
        logger.info("Snapshot task cancelled")


async def cleanup_loop(
    db: Database,
    interval: float = 86400.0,
    retention_days: int = 30,
) -> None:
    """Prune old snapshots every `interval` seconds (default: daily).

    Runs until cancelled. Handles exceptions without crashing.
    """
    logger.info("Cleanup task started (interval=%ss, retention=%dd)", interval, retention_days)
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                deleted = await db.cleanup_old_snapshots(retention_days)
                if deleted > 0:
                    logger.info("Cleanup: removed %d old snapshots", deleted)
            except Exception:
                logger.exception("Error during snapshot cleanup")
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
