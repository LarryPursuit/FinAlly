"""Tests for LLM client abstraction."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.services.llm import (
    LLMResponse,
    MockLLMClient,
    OpenRouterClient,
    TradeAction,
    WatchlistAction,
    create_llm_client,
)


class TestPydanticModels:
    def test_trade_action_valid(self):
        action = TradeAction(ticker="AAPL", side="buy", quantity=5)
        assert action.ticker == "AAPL"
        assert action.side == "buy"
        assert action.quantity == 5

    def test_trade_action_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=0)

    def test_trade_action_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=-1)

    def test_watchlist_action_valid(self):
        action = WatchlistAction(ticker="TSLA", action="add")
        assert action.ticker == "TSLA"
        assert action.action == "add"

    def test_llm_response_message_only(self):
        resp = LLMResponse(message="Hello there")
        assert resp.message == "Hello there"
        assert resp.trades == []
        assert resp.watchlist_changes == []

    def test_llm_response_full(self):
        resp = LLMResponse(
            message="Done!",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )
        assert len(resp.trades) == 1
        assert len(resp.watchlist_changes) == 1

    def test_llm_response_from_json(self):
        raw = '{"message": "OK", "trades": [{"ticker": "MSFT", "side": "sell", "quantity": 3}]}'
        resp = LLMResponse.model_validate_json(raw)
        assert resp.message == "OK"
        assert resp.trades[0].ticker == "MSFT"
        assert resp.watchlist_changes == []

    def test_llm_response_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json('{"trades": []}')


class TestMockLLMClient:
    async def test_buy_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "Buy 5 shares of AAPL"}])
        assert len(resp.trades) == 1
        assert resp.trades[0].ticker == "AAPL"
        assert resp.trades[0].side == "buy"
        assert resp.trades[0].quantity == 5

    async def test_sell_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "Sell 10 MSFT"}])
        assert len(resp.trades) == 1
        assert resp.trades[0].ticker == "MSFT"
        assert resp.trades[0].side == "sell"
        assert resp.trades[0].quantity == 10

    async def test_buy_shares_of_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "buy 3 shares of GOOGL"}])
        assert resp.trades[0].ticker == "GOOGL"
        assert resp.trades[0].quantity == 3

    async def test_add_watchlist_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "Add PYPL to my watchlist"}])
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "PYPL"
        assert resp.watchlist_changes[0].action == "add"

    async def test_watch_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "watch NFLX"}])
        assert resp.watchlist_changes[0].ticker == "NFLX"
        assert resp.watchlist_changes[0].action == "add"

    async def test_remove_watchlist_pattern(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "Remove META from watchlist"}])
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "META"
        assert resp.watchlist_changes[0].action == "remove"

    async def test_generic_response(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "How is my portfolio?"}])
        assert len(resp.trades) == 0
        assert len(resp.watchlist_changes) == 0
        assert "portfolio" in resp.message.lower()

    async def test_ticker_uppercased(self):
        client = MockLLMClient()
        resp = await client.chat([{"role": "user", "content": "buy 1 aapl"}])
        assert resp.trades[0].ticker == "AAPL"


class TestFactory:
    def test_mock_env_returns_mock(self):
        with patch.dict(os.environ, {"LLM_MOCK": "true"}, clear=False):
            client = create_llm_client()
            assert isinstance(client, MockLLMClient)

    def test_mock_env_case_insensitive(self):
        with patch.dict(os.environ, {"LLM_MOCK": "True"}, clear=False):
            client = create_llm_client()
            assert isinstance(client, MockLLMClient)

    def test_api_key_returns_openrouter(self):
        with patch.dict(
            os.environ,
            {"LLM_MOCK": "", "OPENROUTER_API_KEY": "sk-test-key"},
            clear=False,
        ):
            client = create_llm_client()
            assert isinstance(client, OpenRouterClient)

    def test_no_key_returns_mock(self):
        with patch.dict(
            os.environ,
            {"LLM_MOCK": "", "OPENROUTER_API_KEY": ""},
            clear=False,
        ):
            client = create_llm_client()
            assert isinstance(client, MockLLMClient)

    def test_mock_takes_precedence_over_api_key(self):
        with patch.dict(
            os.environ,
            {"LLM_MOCK": "true", "OPENROUTER_API_KEY": "sk-test-key"},
            clear=False,
        ):
            client = create_llm_client()
            assert isinstance(client, MockLLMClient)
