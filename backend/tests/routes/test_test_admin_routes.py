"""Tests for the test-only admin reset route."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.test_admin import ALLOW_TEST_RESET_ENV, create_test_admin_router


@pytest.fixture
def mock_market_data_source():
    source = MagicMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()
    source.start = AsyncMock()
    return source


@pytest.fixture
def admin_app(db, price_cache, mock_market_data_source):
    app = FastAPI()
    router = create_test_admin_router(db, price_cache, mock_market_data_source)
    app.include_router(router)
    return app


class TestResetEndpointGuard:
    async def test_returns_403_when_env_unset(
        self, admin_app, monkeypatch
    ):
        monkeypatch.delenv(ALLOW_TEST_RESET_ENV, raising=False)
        async with AsyncClient(
            transport=ASGITransport(app=admin_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/test/reset")
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    async def test_returns_403_when_env_set_to_false(
        self, admin_app, monkeypatch
    ):
        monkeypatch.setenv(ALLOW_TEST_RESET_ENV, "false")
        async with AsyncClient(
            transport=ASGITransport(app=admin_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/test/reset")
        assert resp.status_code == 403


class TestResetEndpointEnabled:
    async def test_resets_and_reseeds(
        self, admin_app, db, mock_market_data_source, monkeypatch
    ):
        monkeypatch.setenv(ALLOW_TEST_RESET_ENV, "true")

        # Mutate state so we can verify reset wiped it.
        await db.update_cash_balance(Decimal("250.00"))
        await db.upsert_position("AAPL", Decimal("3"), Decimal("190"))
        await db.record_trade("AAPL", "buy", Decimal("3"), Decimal("190"))
        await db.add_chat_message("user", "buy something")
        await db.remove_from_watchlist("NFLX")
        await db.add_to_watchlist("PYPL")

        async with AsyncClient(
            transport=ASGITransport(app=admin_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/test/reset")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Verify state was reset to seed defaults.
        user = await db.get_user()
        assert user is not None
        assert user.cash_balance == Decimal("10000")

        positions = await db.get_positions()
        assert positions == []

        trades = await db.get_trades()
        assert trades == []

        messages = await db.get_recent_messages(limit=50)
        assert messages == []

        tickers = await db.get_watchlist_tickers()
        assert len(tickers) == 10
        assert "NFLX" in tickers
        assert "PYPL" not in tickers

        snapshots = await db.get_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].total_value == Decimal("10000")

        # Market data source should have re-registered the seed tickers.
        assert mock_market_data_source.add_ticker.await_count == 10
