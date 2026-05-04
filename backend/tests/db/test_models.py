"""Tests for database models."""

from decimal import Decimal

from app.db.models import (
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistEntry,
)


class TestUserProfile:
    def test_creation(self):
        user = UserProfile(id="default", cash_balance=Decimal("10000.00"), created_at="2024-01-01T00:00:00Z")
        assert user.id == "default"
        assert user.cash_balance == Decimal("10000.00")

    def test_frozen(self):
        user = UserProfile(id="default", cash_balance=Decimal("10000.00"), created_at="2024-01-01T00:00:00Z")
        try:
            user.cash_balance = Decimal("5000.00")
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_to_dict(self):
        user = UserProfile(id="default", cash_balance=Decimal("10000.50"), created_at="2024-01-01T00:00:00Z")
        d = user.to_dict()
        assert d["id"] == "default"
        assert d["cash_balance"] == 10000.50
        assert isinstance(d["cash_balance"], float)


class TestWatchlistEntry:
    def test_creation(self):
        entry = WatchlistEntry(id="uuid1", user_id="default", ticker="AAPL", added_at="2024-01-01T00:00:00Z")
        assert entry.ticker == "AAPL"

    def test_to_dict(self):
        entry = WatchlistEntry(id="uuid1", user_id="default", ticker="AAPL", added_at="2024-01-01T00:00:00Z")
        d = entry.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["user_id"] == "default"


class TestPosition:
    def test_creation(self):
        pos = Position(
            id="uuid1", user_id="default", ticker="AAPL",
            quantity=Decimal("10"), avg_cost=Decimal("190.50"), updated_at="2024-01-01T00:00:00Z",
        )
        assert pos.quantity == Decimal("10")

    def test_to_dict_converts_decimal_to_float(self):
        pos = Position(
            id="uuid1", user_id="default", ticker="AAPL",
            quantity=Decimal("10"), avg_cost=Decimal("190.50"), updated_at="2024-01-01T00:00:00Z",
        )
        d = pos.to_dict()
        assert isinstance(d["quantity"], float)
        assert isinstance(d["avg_cost"], float)
        assert d["quantity"] == 10.0
        assert d["avg_cost"] == 190.50


class TestTrade:
    def test_creation(self):
        trade = Trade(
            id="uuid1", user_id="default", ticker="AAPL", side="buy",
            quantity=Decimal("5"), price=Decimal("190.25"), executed_at="2024-01-01T00:00:00Z",
        )
        assert trade.side == "buy"
        assert trade.price == Decimal("190.25")

    def test_to_dict(self):
        trade = Trade(
            id="uuid1", user_id="default", ticker="AAPL", side="sell",
            quantity=Decimal("3"), price=Decimal("195.00"), executed_at="2024-01-01T00:00:00Z",
        )
        d = trade.to_dict()
        assert d["side"] == "sell"
        assert d["price"] == 195.0


class TestPortfolioSnapshot:
    def test_creation(self):
        snap = PortfolioSnapshot(
            id="uuid1", user_id="default", total_value=Decimal("12500.75"),
            recorded_at="2024-01-01T00:00:00Z",
        )
        assert snap.total_value == Decimal("12500.75")

    def test_to_dict(self):
        snap = PortfolioSnapshot(
            id="uuid1", user_id="default", total_value=Decimal("12500.75"),
            recorded_at="2024-01-01T00:00:00Z",
        )
        d = snap.to_dict()
        assert d["total_value"] == 12500.75


class TestChatMessage:
    def test_creation(self):
        msg = ChatMessage(
            id="uuid1", user_id="default", role="user",
            content="Buy AAPL", actions=None, created_at="2024-01-01T00:00:00Z",
        )
        assert msg.role == "user"
        assert msg.actions is None

    def test_to_dict_with_actions(self):
        msg = ChatMessage(
            id="uuid1", user_id="default", role="assistant",
            content="Done", actions='{"trades": []}', created_at="2024-01-01T00:00:00Z",
        )
        d = msg.to_dict()
        assert d["actions"] == '{"trades": []}'
