"""Pytest configuration and fixtures."""

import asyncio

import pytest

from app.db.database import Database
from app.market.cache import PriceCache


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def db():
    """In-memory database, initialized and seeded."""
    database = Database(":memory:")
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def price_cache() -> PriceCache:
    """PriceCache seeded with test prices for default tickers."""
    cache = PriceCache()
    test_prices = {
        "AAPL": 190.00,
        "GOOGL": 175.00,
        "MSFT": 420.00,
        "AMZN": 185.00,
        "TSLA": 250.00,
        "NVDA": 800.00,
        "META": 500.00,
        "JPM": 195.00,
        "V": 280.00,
        "NFLX": 600.00,
    }
    for ticker, price in test_prices.items():
        cache.update(ticker, price)
    return cache
