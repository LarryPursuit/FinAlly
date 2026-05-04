"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.database import Database
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.routes import (
    create_chat_router,
    create_health_router,
    create_portfolio_router,
    create_watchlist_router,
)
from app.services.llm import create_llm_client
from app.tasks.snapshots import cleanup_loop, snapshot_loop

logger = logging.getLogger(__name__)

# Default database path: /app/db/finally.db in Docker, or ./db/finally.db locally
DEFAULT_DB_PATH = os.environ.get(
    "DATABASE_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "db" / "finally.db"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    # ── Startup ──────────────────────────────────────────────────────
    db_path = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
    db = Database(db_path)
    await db.initialize()

    price_cache = PriceCache()
    market_data_source = create_market_data_source(price_cache)

    # Load watchlist from DB and start market data
    tickers = await db.get_watchlist_tickers()
    await market_data_source.start(tickers)

    # Start background tasks
    snapshot_task = asyncio.create_task(snapshot_loop(db, price_cache))
    cleanup_task = asyncio.create_task(cleanup_loop(db))

    # Create LLM client
    llm_client = create_llm_client()

    # Mount routers
    stream_router = create_stream_router(price_cache)
    health_router = create_health_router(db, market_data_source)
    portfolio_router = create_portfolio_router(db, price_cache)
    watchlist_router = create_watchlist_router(db, price_cache, market_data_source)
    chat_router = create_chat_router(db, price_cache, market_data_source, llm_client)

    app.include_router(stream_router)
    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)

    # Serve static frontend files if the directory exists
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    logger.info("FinAlly backend started")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    snapshot_task.cancel()
    cleanup_task.cancel()
    await asyncio.gather(snapshot_task, cleanup_task, return_exceptions=True)

    await market_data_source.stop()
    await db.close()
    logger.info("FinAlly backend stopped")


app = FastAPI(
    title="FinAlly",
    description="AI Trading Workstation",
    version="0.1.0",
    lifespan=lifespan,
)
