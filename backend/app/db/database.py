"""Async SQLite database with lazy initialization."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite

from .models import (
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistEntry,
)
from .schema import INDEXES_SQL, SCHEMA_SQL
from .seed import DEFAULT_CASH_BALANCE, DEFAULT_TICKERS, DEFAULT_USER_ID

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class Database:
    """Async SQLite database with lazy schema initialization.

    Usage:
        db = Database(":memory:")  # or path to .db file
        await db.initialize()
        # ... use db ...
        await db.close()
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open connection, create schema if needed, seed default data."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.executescript(INDEXES_SQL)
        await self._conn.commit()
        await self._seed_if_empty()
        logger.info("Database initialized: %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database closed")

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    # ── Seeding ──────────────────────────────────────────────────────────

    async def _seed_if_empty(self) -> None:
        cursor = await self._conn.execute("SELECT COUNT(*) FROM users_profile")
        row = await cursor.fetchone()
        if row[0] > 0:
            return

        now = _now_iso()

        # Create default user
        await self._conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )

        # Seed watchlist
        for ticker in DEFAULT_TICKERS:
            await self._conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (_uuid(), DEFAULT_USER_ID, ticker, now),
            )

        # Seed initial portfolio snapshot
        await self._conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (_uuid(), DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )

        await self._conn.commit()
        logger.info("Seeded default data: user=%s, tickers=%d", DEFAULT_USER_ID, len(DEFAULT_TICKERS))

    # ── User Profile ─────────────────────────────────────────────────────

    async def get_user(self, user_id: str = DEFAULT_USER_ID) -> UserProfile | None:
        cursor = await self._conn.execute(
            "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return UserProfile(
            id=row["id"],
            cash_balance=Decimal(str(row["cash_balance"])),
            created_at=row["created_at"],
        )

    async def update_cash_balance(
        self, amount: Decimal, user_id: str = DEFAULT_USER_ID
    ) -> None:
        """Set the user's cash balance to `amount`."""
        await self._conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (float(amount), user_id),
        )
        await self._conn.commit()

    # ── Watchlist ────────────────────────────────────────────────────────

    async def get_watchlist(self, user_id: str = DEFAULT_USER_ID) -> list[WatchlistEntry]:
        cursor = await self._conn.execute(
            "SELECT id, user_id, ticker, added_at FROM watchlist "
            "WHERE user_id = ? ORDER BY added_at",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            WatchlistEntry(id=r["id"], user_id=r["user_id"], ticker=r["ticker"], added_at=r["added_at"])
            for r in rows
        ]

    async def get_watchlist_tickers(self, user_id: str = DEFAULT_USER_ID) -> list[str]:
        cursor = await self._conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [r["ticker"] for r in rows]

    async def add_to_watchlist(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> WatchlistEntry:
        """Add a ticker to the watchlist. Raises ValueError if already present."""
        now = _now_iso()
        entry_id = _uuid()
        try:
            await self._conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (entry_id, user_id, ticker, now),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError:
            raise ValueError(f"Ticker {ticker} already in watchlist")
        return WatchlistEntry(id=entry_id, user_id=user_id, ticker=ticker, added_at=now)

    async def remove_from_watchlist(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> bool:
        """Remove a ticker from the watchlist. Returns True if removed."""
        cursor = await self._conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    # ── Positions ────────────────────────────────────────────────────────

    async def get_positions(self, user_id: str = DEFAULT_USER_ID) -> list[Position]:
        cursor = await self._conn.execute(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            Position(
                id=r["id"],
                user_id=r["user_id"],
                ticker=r["ticker"],
                quantity=Decimal(str(r["quantity"])),
                avg_cost=Decimal(str(r["avg_cost"])),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_position(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> Position | None:
        cursor = await self._conn.execute(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Position(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            quantity=Decimal(str(row["quantity"])),
            avg_cost=Decimal(str(row["avg_cost"])),
            updated_at=row["updated_at"],
        )

    async def upsert_position(
        self,
        ticker: str,
        quantity: Decimal,
        avg_cost: Decimal,
        user_id: str = DEFAULT_USER_ID,
    ) -> Position:
        """Insert or update a position. quantity must be > 0."""
        now = _now_iso()
        pos_id = _uuid()
        await self._conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (user_id, ticker) DO UPDATE SET "
            "quantity = excluded.quantity, avg_cost = excluded.avg_cost, updated_at = excluded.updated_at",
            (pos_id, user_id, ticker, float(quantity), float(avg_cost), now),
        )
        await self._conn.commit()
        return await self.get_position(ticker, user_id)

    async def delete_position(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> bool:
        """Delete a position entirely (full sell). Returns True if deleted."""
        cursor = await self._conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    # ── Trades ───────────────────────────────────────────────────────────

    async def record_trade(
        self,
        ticker: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        user_id: str = DEFAULT_USER_ID,
    ) -> Trade:
        """Record a trade in the append-only log."""
        now = _now_iso()
        trade_id = _uuid()
        await self._conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side, float(quantity), float(price), now),
        )
        await self._conn.commit()
        return Trade(
            id=trade_id,
            user_id=user_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            executed_at=now,
        )

    async def get_trades(self, user_id: str = DEFAULT_USER_ID) -> list[Trade]:
        cursor = await self._conn.execute(
            "SELECT id, user_id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            Trade(
                id=r["id"],
                user_id=r["user_id"],
                ticker=r["ticker"],
                side=r["side"],
                quantity=Decimal(str(r["quantity"])),
                price=Decimal(str(r["price"])),
                executed_at=r["executed_at"],
            )
            for r in rows
        ]

    # ── Portfolio Snapshots ──────────────────────────────────────────────

    async def record_snapshot(
        self, total_value: Decimal, user_id: str = DEFAULT_USER_ID
    ) -> PortfolioSnapshot:
        now = _now_iso()
        snap_id = _uuid()
        await self._conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (snap_id, user_id, float(total_value), now),
        )
        await self._conn.commit()
        return PortfolioSnapshot(
            id=snap_id, user_id=user_id, total_value=total_value, recorded_at=now,
        )

    async def get_snapshots(self, user_id: str = DEFAULT_USER_ID) -> list[PortfolioSnapshot]:
        cursor = await self._conn.execute(
            "SELECT id, user_id, total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            PortfolioSnapshot(
                id=r["id"],
                user_id=r["user_id"],
                total_value=Decimal(str(r["total_value"])),
                recorded_at=r["recorded_at"],
            )
            for r in rows
        ]

    async def cleanup_old_snapshots(
        self, retention_days: int = 30, user_id: str = DEFAULT_USER_ID
    ) -> int:
        """Delete snapshots older than retention_days. Returns count deleted."""
        cutoff = datetime.now(timezone.utc)
        # Subtract days manually to avoid importing timedelta at module level
        from datetime import timedelta

        cutoff = (cutoff - timedelta(days=retention_days)).isoformat()
        cursor = await self._conn.execute(
            "DELETE FROM portfolio_snapshots WHERE user_id = ? AND recorded_at < ?",
            (user_id, cutoff),
        )
        await self._conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Cleaned up %d old snapshots for user %s", deleted, user_id)
        return deleted

    # ── Chat Messages ────────────────────────────────────────────────────

    async def add_chat_message(
        self,
        role: str,
        content: str,
        actions: str | None = None,
        user_id: str = DEFAULT_USER_ID,
    ) -> ChatMessage:
        now = _now_iso()
        msg_id = _uuid()
        await self._conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, user_id, role, content, actions, now),
        )
        await self._conn.commit()
        return ChatMessage(
            id=msg_id, user_id=user_id, role=role, content=content,
            actions=actions, created_at=now,
        )

    async def get_recent_messages(
        self, limit: int = 20, user_id: str = DEFAULT_USER_ID
    ) -> list[ChatMessage]:
        """Get recent chat messages in chronological order."""
        cursor = await self._conn.execute(
            "SELECT id, user_id, role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        messages = [
            ChatMessage(
                id=r["id"],
                user_id=r["user_id"],
                role=r["role"],
                content=r["content"],
                actions=r["actions"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
        return list(reversed(messages))  # Return in chronological order
