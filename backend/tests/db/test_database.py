"""Tests for the Database class."""

from decimal import Decimal

import pytest


class TestDatabaseInit:
    async def test_initialize_creates_tables(self, db):
        """Database initializes with schema and seeds."""
        user = await db.get_user()
        assert user is not None
        assert user.id == "default"
        assert user.cash_balance == Decimal("10000")

    async def test_seed_creates_watchlist(self, db):
        tickers = await db.get_watchlist_tickers()
        assert len(tickers) == 10
        assert "AAPL" in tickers
        assert "NFLX" in tickers

    async def test_seed_creates_initial_snapshot(self, db):
        snapshots = await db.get_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].total_value == Decimal("10000")

    async def test_seed_is_idempotent(self, db):
        """Calling initialize again should not duplicate seed data."""
        await db.initialize()
        tickers = await db.get_watchlist_tickers()
        assert len(tickers) == 10

    async def test_is_connected(self, db):
        assert db.is_connected is True
        await db.close()
        assert db.is_connected is False


class TestUserProfile:
    async def test_get_user(self, db):
        user = await db.get_user()
        assert user.cash_balance == Decimal("10000")

    async def test_get_nonexistent_user(self, db):
        user = await db.get_user("nobody")
        assert user is None

    async def test_update_cash_balance(self, db):
        await db.update_cash_balance(Decimal("8500.50"))
        user = await db.get_user()
        assert user.cash_balance == Decimal("8500.5")


class TestWatchlist:
    async def test_get_watchlist(self, db):
        entries = await db.get_watchlist()
        assert len(entries) == 10
        assert entries[0].user_id == "default"

    async def test_add_to_watchlist(self, db):
        entry = await db.add_to_watchlist("PYPL")
        assert entry.ticker == "PYPL"
        tickers = await db.get_watchlist_tickers()
        assert "PYPL" in tickers

    async def test_add_duplicate_raises(self, db):
        with pytest.raises(ValueError, match="already in watchlist"):
            await db.add_to_watchlist("AAPL")

    async def test_remove_from_watchlist(self, db):
        removed = await db.remove_from_watchlist("AAPL")
        assert removed is True
        tickers = await db.get_watchlist_tickers()
        assert "AAPL" not in tickers

    async def test_remove_nonexistent(self, db):
        removed = await db.remove_from_watchlist("ZZZZ")
        assert removed is False


class TestPositions:
    async def test_no_positions_initially(self, db):
        positions = await db.get_positions()
        assert len(positions) == 0

    async def test_upsert_new_position(self, db):
        pos = await db.upsert_position("AAPL", Decimal("10"), Decimal("190.50"))
        assert pos.ticker == "AAPL"
        assert pos.quantity == Decimal("10")
        assert pos.avg_cost == Decimal("190.5")

    async def test_upsert_updates_existing(self, db):
        await db.upsert_position("AAPL", Decimal("10"), Decimal("190.50"))
        pos = await db.upsert_position("AAPL", Decimal("15"), Decimal("192.00"))
        assert pos.quantity == Decimal("15")
        assert pos.avg_cost == Decimal("192")

    async def test_get_position(self, db):
        await db.upsert_position("AAPL", Decimal("10"), Decimal("190.50"))
        pos = await db.get_position("AAPL")
        assert pos is not None
        assert pos.ticker == "AAPL"

    async def test_get_nonexistent_position(self, db):
        pos = await db.get_position("ZZZZ")
        assert pos is None

    async def test_delete_position(self, db):
        await db.upsert_position("AAPL", Decimal("10"), Decimal("190.50"))
        deleted = await db.delete_position("AAPL")
        assert deleted is True
        pos = await db.get_position("AAPL")
        assert pos is None

    async def test_delete_nonexistent_position(self, db):
        deleted = await db.delete_position("ZZZZ")
        assert deleted is False


class TestTrades:
    async def test_record_trade(self, db):
        trade = await db.record_trade("AAPL", "buy", Decimal("5"), Decimal("190.25"))
        assert trade.ticker == "AAPL"
        assert trade.side == "buy"
        assert trade.quantity == Decimal("5")

    async def test_get_trades(self, db):
        await db.record_trade("AAPL", "buy", Decimal("5"), Decimal("190.25"))
        await db.record_trade("GOOGL", "buy", Decimal("3"), Decimal("175.00"))
        trades = await db.get_trades()
        assert len(trades) == 2

    async def test_trades_ordered_desc(self, db):
        await db.record_trade("AAPL", "buy", Decimal("5"), Decimal("190.25"))
        await db.record_trade("GOOGL", "buy", Decimal("3"), Decimal("175.00"))
        trades = await db.get_trades()
        # Most recent first
        assert trades[0].ticker == "GOOGL"


class TestSnapshots:
    async def test_record_snapshot(self, db):
        snap = await db.record_snapshot(Decimal("12500.75"))
        assert snap.total_value == Decimal("12500.75")

    async def test_get_snapshots_ordered(self, db):
        # Already has seed snapshot
        await db.record_snapshot(Decimal("10100.00"))
        await db.record_snapshot(Decimal("10200.00"))
        snapshots = await db.get_snapshots()
        assert len(snapshots) == 3  # seed + 2
        # Chronological order
        assert snapshots[0].total_value == Decimal("10000")

    async def test_cleanup_old_snapshots(self, db):
        # All current snapshots are recent, so cleanup should delete 0
        deleted = await db.cleanup_old_snapshots(retention_days=30)
        assert deleted == 0


class TestChatMessages:
    async def test_add_chat_message(self, db):
        msg = await db.add_chat_message("user", "Buy AAPL")
        assert msg.role == "user"
        assert msg.content == "Buy AAPL"
        assert msg.actions is None

    async def test_add_message_with_actions(self, db):
        msg = await db.add_chat_message("assistant", "Done", actions='{"trades": []}')
        assert msg.actions == '{"trades": []}'

    async def test_get_recent_messages_chronological(self, db):
        await db.add_chat_message("user", "msg1")
        await db.add_chat_message("assistant", "msg2")
        await db.add_chat_message("user", "msg3")
        messages = await db.get_recent_messages()
        assert len(messages) == 3
        assert messages[0].content == "msg1"
        assert messages[2].content == "msg3"

    async def test_get_recent_messages_limit(self, db):
        for i in range(5):
            await db.add_chat_message("user", f"msg{i}")
        messages = await db.get_recent_messages(limit=3)
        assert len(messages) == 3
        # Should be most recent 3, in chronological order
        assert messages[0].content == "msg2"
        assert messages[2].content == "msg4"
