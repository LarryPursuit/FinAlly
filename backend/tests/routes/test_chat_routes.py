"""Tests for chat routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.chat import create_chat_router
from app.services.llm import (
    LLMClient,
    LLMError,
    LLMResponse,
    MockLLMClient,
    TradeAction,
)


class FixedLLMClient(LLMClient):
    """Returns a pre-configured LLMResponse for route testing."""

    def __init__(self, response: LLMResponse) -> None:
        self._response = response

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        return self._response


class FailingLLMClient(LLMClient):
    """Raises LLMError on every call."""

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        raise LLMError("API unavailable")


@pytest.fixture
def mock_market_data_source():
    source = MagicMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()
    return source


@pytest.fixture
def chat_app(db, price_cache, mock_market_data_source):
    """App with MockLLMClient for pattern-matched responses."""
    app = FastAPI()
    llm = MockLLMClient()
    router = create_chat_router(db, price_cache, mock_market_data_source, llm)
    app.include_router(router)
    return app


@pytest.fixture
def chat_app_with_llm(db, price_cache, mock_market_data_source):
    """Factory to create app with a specific LLM client."""
    def _make(llm_client: LLMClient):
        app = FastAPI()
        router = create_chat_router(db, price_cache, mock_market_data_source, llm_client)
        app.include_router(router)
        return app
    return _make


class TestPostChat:
    async def test_basic_response(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": "How is my portfolio?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert isinstance(data["trades"], list)
        assert isinstance(data["watchlist_changes"], list)
        assert isinstance(data["errors"], list)

    async def test_buy_via_chat(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": "Buy 5 shares of AAPL"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["success"] is True
        assert data["trades"][0]["ticker"] == "AAPL"

    async def test_sell_without_position(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": "Sell 5 AAPL"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["trades"][0]["success"] is False
        assert len(data["errors"]) == 1

    async def test_watchlist_add(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            # Remove PYPL first if present, then add via chat
            resp = await client.post("/api/chat", json={"message": "Add PYPL to my watchlist"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["watchlist_changes"]) == 1

    async def test_empty_message_rejected(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    async def test_missing_message_field(self, chat_app):
        async with AsyncClient(
            transport=ASGITransport(app=chat_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={})
        assert resp.status_code == 422


class TestChatErrors:
    async def test_llm_error_returns_500(self, chat_app_with_llm):
        app = chat_app_with_llm(FailingLLMClient())
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 500
        data = resp.json()
        assert data["code"] == "LLM_ERROR"
        assert "unavailable" in data["error"].lower()

    async def test_trade_with_response(self, chat_app_with_llm):
        """Verify a FixedLLMClient trade flows through the route."""
        llm = FixedLLMClient(LLMResponse(
            message="Buying AAPL.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=3)],
        ))
        app = chat_app_with_llm(llm)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={"message": "buy AAPL"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["trades"][0]["success"] is True
        assert data["trades"][0]["price"] == 190.0
