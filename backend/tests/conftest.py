"""Pytest configuration and shared fixtures."""

import asyncio

import pytest

from app.market.cache import PriceCache


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def price_cache() -> PriceCache:
    """Empty PriceCache for tests that need a fresh cache."""
    return PriceCache()


@pytest.fixture
def populated_cache() -> PriceCache:
    """PriceCache pre-loaded with AAPL and GOOGL prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.00)
    return cache
