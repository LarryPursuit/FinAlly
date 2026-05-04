"""Tests for portfolio service."""

from decimal import Decimal

from app.market.cache import PriceCache
from app.services.portfolio import compute_total_value, get_portfolio_summary


class TestComputeTotalValue:
    async def test_cash_only(self, db, price_cache):
        """No positions: total = cash balance."""
        total = await compute_total_value(db, price_cache)
        assert total == Decimal("10000")

    async def test_with_positions(self, db, price_cache):
        """Cash + positions * current prices."""
        await db.upsert_position("AAPL", Decimal("10"), Decimal("185.00"))
        total = await compute_total_value(db, price_cache)
        # 10000 + 10 * 190.00 = 11900
        assert total == Decimal("10000") + Decimal("10") * Decimal("190.0")

    async def test_nonexistent_user(self, db, price_cache):
        total = await compute_total_value(db, price_cache, "nobody")
        assert total == Decimal("0")


class TestGetPortfolioSummary:
    async def test_empty_portfolio(self, db, price_cache):
        summary = await get_portfolio_summary(db, price_cache)
        assert summary["cash_balance"] == 10000.00
        assert summary["total_value"] == 10000.00
        assert summary["positions"] == []

    async def test_with_position(self, db, price_cache):
        await db.upsert_position("AAPL", Decimal("10"), Decimal("185.00"))
        summary = await get_portfolio_summary(db, price_cache)
        assert summary["cash_balance"] == 10000.00
        assert len(summary["positions"]) == 1
        pos = summary["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10.0
        assert pos["current_price"] == 190.00
        assert pos["market_value"] == 1900.00
        assert pos["unrealized_pnl"] == 50.00  # (190-185)*10

    async def test_pnl_percentage(self, db, price_cache):
        await db.upsert_position("AAPL", Decimal("10"), Decimal("185.00"))
        summary = await get_portfolio_summary(db, price_cache)
        pos = summary["positions"][0]
        # (190-185)/185 * 100 = 2.70%
        assert pos["unrealized_pnl_pct"] == 2.7

    async def test_position_without_price(self, db):
        """If price cache has no price, use avg_cost as fallback."""
        empty_cache = PriceCache()
        await db.upsert_position("ZZZZ", Decimal("5"), Decimal("100.00"))
        summary = await get_portfolio_summary(db, empty_cache)
        pos = summary["positions"][0]
        assert pos["current_price"] == 100.00
        assert pos["unrealized_pnl"] == 0.0
