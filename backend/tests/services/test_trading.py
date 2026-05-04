"""Tests for trading service."""

import asyncio
from decimal import Decimal

import pytest

from app.services.trading import execute_trade


class TestBuy:
    async def test_buy_success(self, db, price_cache):
        result = await execute_trade(db, price_cache, "AAPL", "buy", 5)
        assert result["success"] is True
        assert result["trade"]["side"] == "buy"
        assert result["trade"]["quantity"] == 5.0
        assert result["new_cash_balance"] == 10000 - 5 * 190.00
        assert result["new_position"]["ticker"] == "AAPL"
        assert result["new_position"]["quantity"] == 5.0

    async def test_buy_insufficient_cash(self, db, price_cache):
        with pytest.raises(ValueError, match="Insufficient cash"):
            await execute_trade(db, price_cache, "NVDA", "buy", 100)
            # 100 * 800 = 80000 > 10000

    async def test_buy_updates_avg_cost(self, db, price_cache):
        """Buying more of an existing position updates weighted avg cost."""
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        # Update AAPL price to 200
        price_cache.update("AAPL", 200.00)
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        # avg = (190*10 + 200*10) / 20 = 195
        result_pos = (await db.get_position("AAPL"))
        assert result_pos.quantity == Decimal("20")
        assert result_pos.avg_cost == Decimal("195")

    async def test_buy_no_price_raises(self, db, price_cache):
        with pytest.raises(ValueError, match="No price"):
            await execute_trade(db, price_cache, "ZZZZ", "buy", 1)

    async def test_buy_records_trade(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 5)
        trades = await db.get_trades()
        assert len(trades) == 1
        assert trades[0].ticker == "AAPL"

    async def test_buy_records_snapshot(self, db, price_cache):
        initial_snapshots = await db.get_snapshots()
        await execute_trade(db, price_cache, "AAPL", "buy", 5)
        snapshots = await db.get_snapshots()
        assert len(snapshots) == len(initial_snapshots) + 1


class TestSell:
    async def test_sell_success(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        result = await execute_trade(db, price_cache, "AAPL", "sell", 5)
        assert result["success"] is True
        assert result["new_position"]["quantity"] == 5.0

    async def test_sell_all_deletes_position(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        result = await execute_trade(db, price_cache, "AAPL", "sell", 10)
        assert result["new_position"] is None
        pos = await db.get_position("AAPL")
        assert pos is None

    async def test_sell_insufficient_shares(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 5)
        with pytest.raises(ValueError, match="Insufficient shares"):
            await execute_trade(db, price_cache, "AAPL", "sell", 10)

    async def test_sell_no_position(self, db, price_cache):
        with pytest.raises(ValueError, match="No position"):
            await execute_trade(db, price_cache, "AAPL", "sell", 1)

    async def test_sell_adds_cash(self, db, price_cache):
        await execute_trade(db, price_cache, "AAPL", "buy", 10)
        result = await execute_trade(db, price_cache, "AAPL", "sell", 5)
        # Started 10000, bought 10*190=1900, sold 5*190=950
        expected = 10000 - 10 * 190 + 5 * 190
        assert result["new_cash_balance"] == expected


class TestConcurrency:
    async def test_concurrent_buys_serialized(self, db, price_cache):
        """Two concurrent buys should both succeed if cash allows."""
        results = await asyncio.gather(
            execute_trade(db, price_cache, "AAPL", "buy", 5),
            execute_trade(db, price_cache, "AAPL", "buy", 5),
        )
        assert all(r["success"] for r in results)
        user = await db.get_user()
        # 10000 - 2 * (5 * 190) = 10000 - 1900 = 8100
        assert user.cash_balance == Decimal("8100")

    async def test_concurrent_buy_fails_when_cash_exhausted(self, db, price_cache):
        """When two buys compete and cash is tight, one should fail."""
        # With 10000 cash and NVDA at 800, buying 12 costs 9600
        # Two buys of 12 can't both succeed
        with pytest.raises(ValueError, match="Insufficient cash"):
            await asyncio.gather(
                execute_trade(db, price_cache, "NVDA", "buy", 12),
                execute_trade(db, price_cache, "NVDA", "buy", 12),
            )
