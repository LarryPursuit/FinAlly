"""LLM client abstraction with OpenRouter and mock implementations."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Structured Output Models ─────────────────────────────────────────────


class TradeAction(BaseModel):
    """A trade the LLM wants to execute."""

    ticker: str
    side: str  # "buy" or "sell"
    quantity: int = Field(gt=0)


class WatchlistAction(BaseModel):
    """A watchlist change the LLM wants to make."""

    ticker: str
    action: str  # "add" or "remove"


class LLMResponse(BaseModel):
    """Structured response from the LLM."""

    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistAction] = Field(default_factory=list)


# ── Custom Exception ─────────────────────────────────────────────────────


class LLMError(Exception):
    """Raised when the LLM call fails."""


# ── Abstract Base Class ──────────────────────────────────────────────────


class LLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Send messages and return a structured response."""


# ── OpenRouter Implementation ────────────────────────────────────────────


class OpenRouterClient(LLMClient):
    """Real LLM client via LiteLLM → OpenRouter → Cerebras."""

    MODEL = "openrouter/openai/gpt-oss-120b"
    EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        from litellm import completion

        try:
            response = await asyncio.to_thread(
                completion,
                model=self.MODEL,
                messages=messages,
                response_format=LLMResponse,
                reasoning_effort="low",
                extra_body=self.EXTRA_BODY,
                api_key=self._api_key,
            )
            content = response.choices[0].message.content
            return LLMResponse.model_validate_json(content)
        except Exception as exc:
            logger.exception("LLM call failed")
            raise LLMError(f"LLM call failed: {exc}") from exc


# ── Mock Implementation ──────────────────────────────────────────────────

# Patterns for deterministic mock responses
_BUY_RE = re.compile(r"buy\s+(\d+)\s+(?:shares?\s+(?:of\s+)?)?([A-Za-z.]+)", re.IGNORECASE)
_SELL_RE = re.compile(r"sell\s+(\d+)\s+(?:shares?\s+(?:of\s+)?)?([A-Za-z.]+)", re.IGNORECASE)
_ADD_RE = re.compile(r"(?:add|watch)\s+([A-Za-z.]+)", re.IGNORECASE)
_REMOVE_RE = re.compile(r"(?:remove|unwatch)\s+([A-Za-z.]+)", re.IGNORECASE)


class MockLLMClient(LLMClient):
    """Deterministic mock for testing and development without API keys."""

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        user_msg = messages[-1]["content"]

        # Check buy pattern
        match = _BUY_RE.search(user_msg)
        if match:
            qty, ticker = int(match.group(1)), match.group(2).upper()
            return LLMResponse(
                message=f"I'll buy {qty} shares of {ticker} for you.",
                trades=[TradeAction(ticker=ticker, side="buy", quantity=qty)],
            )

        # Check sell pattern
        match = _SELL_RE.search(user_msg)
        if match:
            qty, ticker = int(match.group(1)), match.group(2).upper()
            return LLMResponse(
                message=f"I'll sell {qty} shares of {ticker} for you.",
                trades=[TradeAction(ticker=ticker, side="sell", quantity=qty)],
            )

        # Check add watchlist pattern
        match = _ADD_RE.search(user_msg)
        if match:
            ticker = match.group(1).upper()
            return LLMResponse(
                message=f"I'll add {ticker} to your watchlist.",
                watchlist_changes=[WatchlistAction(ticker=ticker, action="add")],
            )

        # Check remove watchlist pattern
        match = _REMOVE_RE.search(user_msg)
        if match:
            ticker = match.group(1).upper()
            return LLMResponse(
                message=f"I'll remove {ticker} from your watchlist.",
                watchlist_changes=[WatchlistAction(ticker=ticker, action="remove")],
            )

        # Default conversational response
        return LLMResponse(
            message=(
                "Your portfolio is looking good! I can help you buy or sell shares, "
                "or manage your watchlist. Just let me know what you'd like to do."
            ),
        )


# ── Factory ──────────────────────────────────────────────────────────────


def create_llm_client() -> LLMClient:
    """Create an LLM client based on environment configuration.

    - LLM_MOCK=true → MockLLMClient
    - OPENROUTER_API_KEY set → OpenRouterClient
    - Fallback → MockLLMClient
    """
    if os.environ.get("LLM_MOCK", "").lower() == "true":
        logger.info("Using mock LLM client (LLM_MOCK=true)")
        return MockLLMClient()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        logger.info("Using OpenRouter LLM client")
        return OpenRouterClient(api_key)

    logger.info("Using mock LLM client (no API key)")
    return MockLLMClient()
