"""Chat orchestration: context building, history trimming, LLM call, auto-execution."""

from __future__ import annotations

import json
import logging

from app.db.database import Database
from app.db.seed import DEFAULT_USER_ID
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.services.llm import LLMClient, LLMResponse
from app.services.portfolio import get_portfolio_summary
from app.services.trading import execute_trade
from app.validation import validate_ticker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant for a simulated trading workstation. "
    "You help users analyze their portfolio, execute trades, and manage their watchlist.\n\n"
    "Guidelines:\n"
    "- Be concise and data-driven\n"
    "- When the user asks to buy or sell, include the trade in your response\n"
    "- When the user asks to add or remove a ticker from the watchlist, include the change\n"
    "- Analyze portfolio composition, risk concentration, and P&L when asked\n"
    "- Always respond with valid structured JSON matching the response schema"
)

TOKEN_BUDGET = 4000
MAX_MESSAGES = 25


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return len(text) // 4


async def _build_context(
    db: Database, price_cache: PriceCache, user_id: str,
) -> str:
    """Build a portfolio context string for the LLM system prompt."""
    summary = await get_portfolio_summary(db, price_cache, user_id)

    if "error" in summary:
        return "Portfolio data unavailable."

    lines = [
        f"Cash: ${summary['cash_balance']:,.2f}",
        f"Total portfolio value: ${summary['total_value']:,.2f}",
    ]

    if summary["positions"]:
        lines.append("Positions:")
        for p in summary["positions"]:
            lines.append(
                f"  {p['ticker']}: {p['quantity']} shares @ avg ${p['avg_cost']:.2f}, "
                f"current ${p['current_price']:.2f}, "
                f"P&L ${p['unrealized_pnl']:.2f} ({p['unrealized_pnl_pct']:.1f}%)"
            )
    else:
        lines.append("No open positions.")

    # Include watchlist
    tickers = await db.get_watchlist_tickers(user_id)
    if tickers:
        watchlist_parts = []
        for t in tickers:
            price = price_cache.get_price(t)
            if price is not None:
                watchlist_parts.append(f"{t} (${price:.2f})")
            else:
                watchlist_parts.append(t)
        lines.append(f"Watchlist: {', '.join(watchlist_parts)}")

    return "\n".join(lines)


async def _build_history(db: Database, user_id: str) -> list[dict[str, str]]:
    """Load recent messages and trim to fit within the token budget."""
    messages = await db.get_recent_messages(limit=MAX_MESSAGES, user_id=user_id)
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Trim oldest messages until under budget
    while _estimate_tokens(str(history)) > TOKEN_BUDGET and len(history) > 1:
        history.pop(0)

    return history


async def _execute_trades(
    db: Database,
    price_cache: PriceCache,
    llm_response: LLMResponse,
    user_id: str,
) -> list[dict]:
    """Execute trades from LLM response best-effort, returning results."""
    results = []
    for trade in llm_response.trades:
        try:
            result = await execute_trade(
                db, price_cache, trade.ticker, trade.side, trade.quantity, user_id,
            )
            results.append({
                **trade.model_dump(),
                "success": True,
                "price": result["trade"]["price"],
            })
        except (ValueError, Exception) as exc:
            logger.warning("Trade execution failed: %s", exc)
            results.append({
                **trade.model_dump(),
                "success": False,
                "error": str(exc),
            })
    return results


async def _execute_watchlist_changes(
    db: Database,
    market_data_source: MarketDataSource,
    llm_response: LLMResponse,
    user_id: str,
) -> list[dict]:
    """Execute watchlist changes from LLM response best-effort."""
    results = []
    for change in llm_response.watchlist_changes:
        try:
            ticker = validate_ticker(change.ticker)
            if change.action == "add":
                await db.add_to_watchlist(ticker, user_id)
                await market_data_source.add_ticker(ticker)
            elif change.action == "remove":
                await db.remove_from_watchlist(ticker, user_id)
                await market_data_source.remove_ticker(ticker)
            else:
                raise ValueError(f"Unknown watchlist action: {change.action}")
            results.append({**change.model_dump(), "success": True})
        except Exception as exc:
            logger.warning("Watchlist change failed: %s", exc)
            results.append({
                **change.model_dump(),
                "success": False,
                "error": str(exc),
            })
    return results


async def process_chat_message(
    db: Database,
    price_cache: PriceCache,
    market_data_source: MarketDataSource,
    llm_client: LLMClient,
    user_message: str,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Orchestrate a full chat turn: context → LLM → execute → store → respond."""
    # 1. Build portfolio context
    context = await _build_context(db, price_cache, user_id)

    # 2. Get and trim message history
    history = await _build_history(db, user_id)

    # 3. Construct LLM messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
        *history,
        {"role": "user", "content": user_message},
    ]

    # 4. Call LLM
    llm_response = await llm_client.chat(messages)

    # 5. Store user message
    await db.add_chat_message("user", user_message, user_id=user_id)

    # 6. Execute trades (best-effort)
    trade_results = await _execute_trades(db, price_cache, llm_response, user_id)

    # 7. Execute watchlist changes (best-effort)
    watchlist_results = await _execute_watchlist_changes(
        db, market_data_source, llm_response, user_id,
    )

    # 8. Collect errors
    errors = [
        r["error"]
        for r in trade_results + watchlist_results
        if not r.get("success")
    ]

    # 9. Store assistant message with actions
    actions = json.dumps({
        "trades": trade_results,
        "watchlist_changes": watchlist_results,
    })
    await db.add_chat_message(
        "assistant", llm_response.message, actions=actions, user_id=user_id,
    )

    # 10. Return response
    return {
        "message": llm_response.message,
        "trades": trade_results,
        "watchlist_changes": watchlist_results,
        "errors": errors,
    }
