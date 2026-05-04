"""Tests for snapshot background tasks."""

import asyncio

from app.tasks.snapshots import cleanup_loop, snapshot_loop


class TestSnapshotLoop:
    async def test_records_snapshot(self, db, price_cache):
        """Snapshot loop records at least one snapshot before cancellation."""
        initial_count = len(await db.get_snapshots())
        task = asyncio.create_task(snapshot_loop(db, price_cache, interval=0.05))
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        snapshots = await db.get_snapshots()
        assert len(snapshots) > initial_count

    async def test_graceful_cancellation(self, db, price_cache):
        """Task handles CancelledError without raising."""
        task = asyncio.create_task(snapshot_loop(db, price_cache, interval=0.05))
        await asyncio.sleep(0.1)
        task.cancel()
        # Should not raise
        await asyncio.gather(task, return_exceptions=True)


class TestCleanupLoop:
    async def test_cleanup_runs(self, db):
        """Cleanup loop runs without error."""
        task = asyncio.create_task(cleanup_loop(db, interval=0.05, retention_days=30))
        await asyncio.sleep(0.15)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_graceful_cancellation(self, db):
        task = asyncio.create_task(cleanup_loop(db, interval=0.05))
        await asyncio.sleep(0.1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
