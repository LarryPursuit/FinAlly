"""Tests for health check route."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.health import create_health_router


@pytest.fixture
def mock_market_data_source():
    source = MagicMock()
    source.get_tickers.return_value = ["AAPL", "GOOGL"]
    return source


@pytest.fixture
def health_app(db, mock_market_data_source):
    app = FastAPI()
    router = create_health_router(db, mock_market_data_source)
    app.include_router(router)
    return app


class TestHealthRoute:
    async def test_health_ok(self, health_app):
        async with AsyncClient(
            transport=ASGITransport(app=health_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["market_data"] == "running"

    async def test_health_market_stopped(self, db):
        source = MagicMock()
        source.get_tickers.return_value = []
        app = FastAPI()
        app.include_router(create_health_router(db, source))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/health")
        assert resp.json()["market_data"] == "stopped"
