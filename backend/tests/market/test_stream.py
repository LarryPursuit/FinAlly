"""Tests for SSE streaming generator (_generate_events)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events


class StubRequest:
    """Minimal Request stub whose is_disconnected() returns False N times then True."""

    def __init__(self, iterations_before_disconnect: int) -> None:
        self._remaining = iterations_before_disconnect
        self.client = None

    async def is_disconnected(self) -> bool:
        if self._remaining <= 0:
            return True
        self._remaining -= 1
        return False


class StaticPriceCache(PriceCache):
    """PriceCache whose version never changes (frozen after construction)."""

    def __init__(self) -> None:
        super().__init__()
        self._frozen_version: int | None = None

    def freeze(self) -> None:
        self._frozen_version = super().version

    @property
    def version(self) -> int:
        if self._frozen_version is not None:
            return self._frozen_version
        return super().version


class TestGenerateEvents:
    """Unit tests for _generate_events async generator."""

    @pytest.mark.asyncio
    async def test_heartbeat_emitted_after_interval(self):
        """Heartbeat ': ping\\n\\n' is yielded after heartbeat_interval elapses."""
        cache = StaticPriceCache()
        cache.update("AAPL", 190.0)
        cache.freeze()  # version never changes — no data events

        # Allow enough iterations for the heartbeat to fire.
        # interval=0.05, heartbeat_interval=0.2 → needs ~4 loops to elapse.
        # Give 8 iterations so we're sure it fires; disconnect after that.
        request = StubRequest(iterations_before_disconnect=8)

        events = []
        async for event in _generate_events(
            cache, request, interval=0.05, heartbeat_interval=0.2
        ):
            events.append(event)

        heartbeat_events = [e for e in events if e == ": ping\n\n"]
        assert len(heartbeat_events) >= 1, (
            f"Expected at least one heartbeat ping, got events: {events}"
        )

    @pytest.mark.asyncio
    async def test_data_event_emitted_when_version_changes(self):
        """A 'data: ...' SSE event is yielded when the cache version changes."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)

        iteration = 0

        class VersionChangingRequest:
            client = None

            async def is_disconnected(self) -> bool:
                nonlocal iteration
                iteration += 1
                # Let two loops run, then disconnect
                return iteration > 2

        # Bump version once after the first loop so the generator sees a change
        original_sleep = asyncio.sleep
        sleep_count = 0

        async def patched_sleep(delay: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count == 1:
                cache.update("AAPL", 195.0)
            await original_sleep(0)

        request = VersionChangingRequest()

        events = []
        import unittest.mock as mock

        with mock.patch("asyncio.sleep", side_effect=patched_sleep):
            async for event in _generate_events(
                cache, request, interval=0.05, heartbeat_interval=20.0
            ):
                events.append(event)

        data_events = [e for e in events if e.startswith("data:")]
        assert len(data_events) >= 1, (
            f"Expected at least one data event, got events: {events}"
        )
        assert "AAPL" in data_events[0]

    @pytest.mark.asyncio
    async def test_retry_directive_emitted_first(self):
        """The generator emits the SSE retry directive as its first event."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)

        request = StubRequest(iterations_before_disconnect=1)

        events = []
        async for event in _generate_events(
            cache, request, interval=0.05, heartbeat_interval=20.0
        ):
            events.append(event)
            break  # Only need the first event

        assert events[0] == "retry: 1000\n\n"

    @pytest.mark.asyncio
    async def test_no_heartbeat_before_interval(self):
        """No heartbeat is emitted when fewer loops run than the heartbeat interval."""
        cache = StaticPriceCache()
        cache.update("AAPL", 190.0)
        cache.freeze()

        # Only 2 iterations at interval=0.05, heartbeat_interval=20.0
        # → heartbeat should NOT fire
        request = StubRequest(iterations_before_disconnect=2)

        events = []
        async for event in _generate_events(
            cache, request, interval=0.05, heartbeat_interval=20.0
        ):
            events.append(event)

        heartbeat_events = [e for e in events if e == ": ping\n\n"]
        assert len(heartbeat_events) == 0, (
            f"Expected no heartbeat pings this early, got: {events}"
        )

    @pytest.mark.asyncio
    async def test_disconnected_client_stops_generator(self):
        """Generator stops immediately when is_disconnected returns True."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)

        request = StubRequest(iterations_before_disconnect=0)

        events = []
        async for event in _generate_events(
            cache, request, interval=0.05, heartbeat_interval=20.0
        ):
            events.append(event)

        # Only the initial retry directive should have been emitted
        non_retry = [e for e in events if e != "retry: 1000\n\n"]
        assert len(non_retry) == 0
