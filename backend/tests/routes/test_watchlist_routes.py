"""Tests for watchlist routes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.watchlist import create_watchlist_router


@pytest.fixture
def mock_market_data_source():
    source = MagicMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()
    return source


@pytest.fixture
def watchlist_app(db, price_cache, mock_market_data_source):
    app = FastAPI()
    router = create_watchlist_router(db, price_cache, mock_market_data_source)
    app.include_router(router)
    return app


class TestGetWatchlist:
    async def test_default_watchlist(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tickers"]) == 10
        tickers = [t["ticker"] for t in data["tickers"]]
        assert "AAPL" in tickers

    async def test_watchlist_includes_prices(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/watchlist")
        data = resp.json()
        aapl = next(t for t in data["tickers"] if t["ticker"] == "AAPL")
        assert aapl["current_price"] == 190.0


class TestAddTicker:
    async def test_add_success(self, watchlist_app, mock_market_data_source):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["ticker"] == "PYPL"
        mock_market_data_source.add_ticker.assert_called_once_with("PYPL")

    async def test_add_invalid_ticker(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/watchlist", json={"ticker": "INVALID!!!"})
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_TICKER"

    async def test_add_duplicate(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 400


class TestRemoveTicker:
    async def test_remove_success(self, watchlist_app, mock_market_data_source):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/watchlist/AAPL")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_market_data_source.remove_ticker.assert_called_once_with("AAPL")

    async def test_remove_not_found(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/watchlist/ZZZZ")
        assert resp.status_code == 404
        assert resp.json()["code"] == "TICKER_NOT_FOUND"

    async def test_remove_invalid_ticker(self, watchlist_app):
        async with AsyncClient(
            transport=ASGITransport(app=watchlist_app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/watchlist/INVALID!!!")
        assert resp.status_code == 400
