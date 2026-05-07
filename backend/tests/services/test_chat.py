"""Tests for chat orchestration service."""

from __future__ import annotations

import json

from app.market.interface import MarketDataSource
from app.services.chat import (
    _build_context,
    _build_history,
    _estimate_tokens,
    process_chat_message,
)
from app.services.llm import (
    LLMClient,
    LLMResponse,
    MockLLMClient,
    TradeAction,
    WatchlistAction,
)
from app.services.trading import execute_trade

# ── Helpers ───────────────────────────────────────────────────────────────


class StubMarketDataSource(MarketDataSource):
    """Minimal stub that tracks add/remove calls."""

    def __init__(self) -> None:
        self._tickers: set[str] = set()

    async def start(self, tickers: list[str]) -> None:
        self._tickers = set(tickers)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker)

    def get_tickers(self) -> list[str]:
        return sorted(self._tickers)


class FixedLLMClient(LLMClient):
    """Returns a pre-configured LLMResponse for testing."""

    def __init__(self, response: LLMResponse) -> None:
        self._response = response

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        self.last_messages = messages
        return self._response


# ── Token estimation ──────────────────────────────────────────────────────


class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_typical_string(self):
        assert _estimate_tokens("Hello, world!") == 3  # 13 // 4


# ── Context building ─────────────────────────────────────────────────────


class TestBuildContext:
    async def test_includes_cash_and_value(self, db, price_cache):
        ctx = await _build_context(db, price_cache, "default")
        assert "Cash: $10,000.00" in ctx
        assert "Total portfolio value:" in ctx

    async def test_includes_positions(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 5)
        ctx = await _build_context(db, price_cache, "default")
        assert "AAPL" in ctx
        assert "5" in ctx

    async def test_includes_watchlist(self, db, price_cache):
        ctx = await _build_context(db, price_cache, "default")
        assert "Watchlist:" in ctx
        assert "AAPL" in ctx

    async def test_no_positions_message(self, db, price_cache):
        ctx = await _build_context(db, price_cache, "default")
        assert "No open positions." in ctx


# ── History building ─────────────────────────────────────────────────────


class TestBuildHistory:
    async def test_empty_history(self, db):
        history = await _build_history(db, "default")
        assert history == []

    async def test_includes_messages(self, db):
        await db.add_chat_message("user", "Hello", user_id="default")
        await db.add_chat_message("assistant", "Hi there!", user_id="default")
        history = await _build_history(db, "default")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    async def test_trims_when_over_budget(self, db):
        # Insert many long messages to exceed the token budget
        for i in range(30):
            await db.add_chat_message(
                "user", f"Message {i}: " + "x" * 500, user_id="default",
            )
        history = await _build_history(db, "default")
        # Should have trimmed to fit within TOKEN_BUDGET
        assert len(history) < 30
        # Most recent message should be preserved
        assert "Message 29" in history[-1]["content"]


# ── Chat flow with MockLLMClient ─────────────────────────────────────────


class TestProcessChatMock:
    async def test_basic_chat_response(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "How is my portfolio?",
        )
        assert "message" in result
        assert isinstance(result["trades"], list)
        assert isinstance(result["watchlist_changes"], list)
        assert isinstance(result["errors"], list)

    async def test_buy_via_chat(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Buy 5 shares of AAPL",
        )
        assert len(result["trades"]) == 1
        assert result["trades"][0]["success"] is True
        assert result["trades"][0]["ticker"] == "AAPL"
        assert result["trades"][0]["side"] == "buy"
        # Cash should have decreased
        user = await db.get_user()
        assert float(user.cash_balance) < 10000

    async def test_sell_without_position_collects_error(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Sell 5 AAPL",
        )
        assert len(result["trades"]) == 1
        assert result["trades"][0]["success"] is False
        assert "No position" in result["trades"][0]["error"]
        assert len(result["errors"]) == 1

    async def test_watchlist_add_via_chat(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        # Remove PYPL from watchlist first (if present) to test adding
        await db.remove_from_watchlist("PYPL", "default")
        result = await process_chat_message(
            db, price_cache, mds, llm, "Add PYPL to my watchlist",
        )
        assert len(result["watchlist_changes"]) == 1
        assert result["watchlist_changes"][0]["success"] is True
        assert result["watchlist_changes"][0]["ticker"] == "PYPL"
        # Verify the ticker was added to market data source
        assert "PYPL" in mds.get_tickers()

    async def test_watchlist_remove_via_chat(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Remove AAPL from watchlist",
        )
        assert len(result["watchlist_changes"]) == 1
        assert result["watchlist_changes"][0]["success"] is True
        # Verify AAPL no longer in watchlist
        tickers = await db.get_watchlist_tickers("default")
        assert "AAPL" not in tickers

    async def test_messages_stored_in_db(self, db, price_cache):
        llm = MockLLMClient()
        mds = StubMarketDataSource()
        await process_chat_message(
            db, price_cache, mds, llm, "How is my portfolio?",
        )
        messages = await db.get_recent_messages(limit=10, user_id="default")
        assert len(messages) == 2  # user + assistant
        assert messages[0].role == "user"
        assert messages[0].content == "How is my portfolio?"
        assert messages[1].role == "assistant"
        # Assistant message should have actions JSON
        assert messages[1].actions is not None
        actions = json.loads(messages[1].actions)
        assert "trades" in actions
        assert "watchlist_changes" in actions


# ── Chat flow with FixedLLMClient ────────────────────────────────────────


class TestProcessChatFixed:
    async def test_trade_failure_still_saves_message(self, db, price_cache):
        """Even when a trade fails, both messages should be stored."""
        llm = FixedLLMClient(LLMResponse(
            message="Selling 100 shares of ZZZZ.",
            trades=[TradeAction(ticker="ZZZZ", side="sell", quantity=100)],
        ))
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Sell 100 ZZZZ",
        )
        assert result["trades"][0]["success"] is False
        # Messages should still be saved
        messages = await db.get_recent_messages(limit=10, user_id="default")
        assert len(messages) == 2

    async def test_multiple_trades_best_effort(self, db, price_cache):
        """Multiple trades execute best-effort: first succeeds, second fails."""
        llm = FixedLLMClient(LLMResponse(
            message="Executing trades.",
            trades=[
                TradeAction(ticker="AAPL", side="buy", quantity=5),
                TradeAction(ticker="ZZZZ", side="buy", quantity=5),  # No price
            ],
        ))
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Buy AAPL and ZZZZ",
        )
        assert result["trades"][0]["success"] is True
        assert result["trades"][1]["success"] is False
        assert len(result["errors"]) == 1

    async def test_watchlist_duplicate_add_is_idempotent(self, db, price_cache):
        """Adding a ticker already in the watchlist should succeed (idempotent)."""
        llm = FixedLLMClient(LLMResponse(
            message="Adding AAPL.",
            watchlist_changes=[WatchlistAction(ticker="AAPL", action="add")],
        ))
        mds = StubMarketDataSource()
        result = await process_chat_message(
            db, price_cache, mds, llm, "Add AAPL to watchlist",
        )
        assert result["watchlist_changes"][0]["success"] is True
        assert result["errors"] == []

    async def test_llm_receives_system_prompt_and_context(self, db, price_cache):
        """The LLM should receive a system prompt with portfolio context."""
        llm = FixedLLMClient(LLMResponse(message="Got it."))
        mds = StubMarketDataSource()
        await process_chat_message(
            db, price_cache, mds, llm, "Hello",
        )
        messages = llm.last_messages
        assert messages[0]["role"] == "system"
        assert "FinAlly" in messages[0]["content"]
        assert "Cash:" in messages[0]["content"]
        # Last message should be the user message
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hello"

    async def test_llm_receives_history(self, db, price_cache):
        """Prior chat messages should appear in the LLM messages."""
        await db.add_chat_message("user", "First message", user_id="default")
        await db.add_chat_message("assistant", "First reply", user_id="default")
        llm = FixedLLMClient(LLMResponse(message="OK."))
        mds = StubMarketDataSource()
        await process_chat_message(
            db, price_cache, mds, llm, "Second message",
        )
        messages = llm.last_messages
        # System + 2 history + 1 new user message = 4
        assert len(messages) == 4
        assert messages[1]["content"] == "First message"
        assert messages[2]["content"] == "First reply"
