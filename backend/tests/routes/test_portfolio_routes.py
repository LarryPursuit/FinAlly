"""Tests for portfolio routes."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.portfolio import create_portfolio_router
from app.services.trading import execute_trade


@pytest.fixture
def portfolio_app(db, price_cache):
    app = FastAPI()
    router = create_portfolio_router(db, price_cache)
    app.include_router(router)
    return app


class TestGetPortfolio:
    async def test_empty_portfolio(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_balance"] == 10000.00
        assert data["positions"] == []

    async def test_portfolio_with_position(self, db, price_cache, portfolio_app):
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/portfolio")
        data = resp.json()
        assert len(data["positions"]) == 1
        assert data["positions"][0]["ticker"] == "AAPL"


class TestPostTrade:
    async def test_buy_success(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_invalid_ticker(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "INVALID!!!", "quantity": 5, "side": "buy"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_TICKER"

    async def test_invalid_side(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "hold"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_SIDE"

    async def test_invalid_quantity(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 1.5, "side": "buy"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_QUANTITY"

    async def test_insufficient_cash(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "NVDA", "quantity": 100, "side": "buy"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INSUFFICIENT_CASH"

    async def test_sell_no_position(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INSUFFICIENT_SHARES"

    async def test_no_price_available(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/portfolio/trade",
                json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_TICKER"


class TestGetHistory:
    async def test_history_has_seed_snapshot(self, portfolio_app):
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/portfolio/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["snapshots"]) >= 1

    async def test_history_after_trade(self, db, price_cache, portfolio_app):
        await execute_trade(db, price_cache, "AAPL", "buy", 5)
        async with AsyncClient(
            transport=ASGITransport(app=portfolio_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/portfolio/history")
        data = resp.json()
        assert len(data["snapshots"]) >= 2
