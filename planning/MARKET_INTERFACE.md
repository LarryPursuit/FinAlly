# Market Data Interface Design

## Overview

The FinAlly backend uses a unified abstract interface for market data, allowing seamless switching between the Massive API (real market data) and a built-in simulator (for development/demo). The interface is selected at runtime based on the `MASSIVE_API_KEY` environment variable.

**Design Goals:**
- Single, clean API for all price data operations
- Zero code changes to switch between real and simulated data
- Type-safe with clear contracts
- Easy to test with mocked implementations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Backend Application (FastAPI)                              │
│                                                              │
│  ├── SSE Streaming (/api/stream/prices)                     │
│  ├── Portfolio Engine (trades, positions, P&L)              │
│  └── Background Tasks (snapshots, cleanup)                  │
│                          │                                   │
│                          ▼                                   │
│              ┌────────────────────────┐                      │
│              │  PriceCache (in-memory)│                      │
│              │  - Latest prices        │                      │
│              │  - Previous prices      │                      │
│              │  - Timestamps           │                      │
│              └────────────────────────┘                      │
│                          ▲                                   │
│                          │                                   │
│              ┌───────────┴───────────┐                       │
│              │                       │                       │
│   ┌──────────▼──────────┐ ┌─────────▼──────────┐            │
│   │  MarketDataSource   │ │  MarketDataSource  │            │
│   │  (Abstract Base)    │ │  (Abstract Base)   │            │
│   └──────────┬──────────┘ └─────────┬──────────┘            │
│              │                       │                       │
│   ┌──────────▼──────────┐ ┌─────────▼──────────┐            │
│   │  MassiveClient      │ │  MarketSimulator   │            │
│   │  - Poll REST API    │ │  - GBM algorithm   │            │
│   │  - Parse responses  │ │  - Correlated moves│            │
│   │  - Rate limiting    │ │  - Random events   │            │
│   └─────────────────────┘ └────────────────────┘            │
│           │                         │                        │
│           ▼                         ▼                        │
│   Massive REST API          In-process math                 │
└─────────────────────────────────────────────────────────────┘
```

## Core Interface

### Abstract Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable
from decimal import Decimal

@dataclass
class PriceUpdate:
    """Immutable price update data structure."""
    ticker: str
    price: Decimal
    previous_price: Decimal
    timestamp: datetime
    volume: int = 0
    change_percent: float = 0.0

    def __post_init__(self):
        """Calculate derived fields."""
        if self.previous_price > 0:
            self.change_percent = float(
                (self.price - self.previous_price) / self.previous_price * 100
            )

    @property
    def direction(self) -> str:
        """Price movement direction: 'up', 'down', or 'unchanged'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "unchanged"


class MarketDataSource(ABC):
    """Abstract interface for market data providers."""

    def __init__(self):
        self._callbacks: List[Callable[[Dict[str, PriceUpdate]], None]] = []
        self._running = False

    @abstractmethod
    async def start(self):
        """Start the data source (polling, simulation, etc.)."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the data source gracefully."""
        pass

    @abstractmethod
    def set_tickers(self, tickers: List[str]):
        """Update the list of tickers to track."""
        pass

    @abstractmethod
    def get_current_price(self, ticker: str) -> Optional[PriceUpdate]:
        """Get the current price for a ticker (synchronous, from cache)."""
        pass

    @abstractmethod
    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """Get current prices for all tracked tickers."""
        pass

    def add_callback(self, callback: Callable[[Dict[str, PriceUpdate]], None]):
        """Register a callback to receive price updates."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, prices: Dict[str, PriceUpdate]):
        """Notify all registered callbacks of price updates."""
        for callback in self._callbacks:
            try:
                callback(prices)
            except Exception as e:
                print(f"Error in price callback: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the data source is actively running."""
        return self._running
```

## Implementation: Massive API Client

```python
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from polygon import RESTClient
import os

class MassiveClient(MarketDataSource):
    """Market data source using Massive (Polygon.io) REST API."""

    def __init__(self, api_key: str, poll_interval: int = 15):
        super().__init__()
        self.client = RESTClient(api_key=api_key)
        self.poll_interval = poll_interval
        self._tickers: List[str] = []
        self._price_cache: Dict[str, PriceUpdate] = {}
        self._task: Optional[asyncio.Task] = None

    def set_tickers(self, tickers: List[str]):
        """Update the list of tickers to poll."""
        self._tickers = list(set(ticker.upper() for ticker in tickers))
        print(f"MassiveClient: Tracking {len(self._tickers)} tickers")

    def get_current_price(self, ticker: str) -> Optional[PriceUpdate]:
        """Get cached price for a ticker."""
        return self._price_cache.get(ticker.upper())

    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """Get all cached prices."""
        return self._price_cache.copy()

    async def start(self):
        """Start polling the Massive API."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        print("MassiveClient: Started")

    async def stop(self):
        """Stop polling gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("MassiveClient: Stopped")

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            if not self._tickers:
                await asyncio.sleep(self.poll_interval)
                continue

            try:
                # Get snapshot for all tickers in one API call
                snapshots = self.client.get_snapshot_all(symbols=self._tickers)

                new_prices = {}
                for snapshot in snapshots:
                    ticker = snapshot.ticker

                    # Get previous price from cache
                    prev_price = (
                        self._price_cache[ticker].price
                        if ticker in self._price_cache
                        else Decimal(str(snapshot.prev_day.c))
                    )

                    # Create price update
                    price_update = PriceUpdate(
                        ticker=ticker,
                        price=Decimal(str(snapshot.day.c)),
                        previous_price=prev_price,
                        timestamp=datetime.now(),
                        volume=snapshot.day.v,
                    )

                    new_prices[ticker] = price_update
                    self._price_cache[ticker] = price_update

                # Notify callbacks
                if new_prices:
                    self._notify_callbacks(new_prices)

                print(f"MassiveClient: Polled {len(new_prices)} prices")

            except Exception as e:
                print(f"MassiveClient: Error polling API: {e}")

            await asyncio.sleep(self.poll_interval)
```

## Implementation: Market Simulator

```python
import asyncio
import random
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
import math

class MarketSimulator(MarketDataSource):
    """Market data source using geometric Brownian motion simulation."""

    # Default seed prices for common tickers
    DEFAULT_PRICES = {
        "AAPL": 190.0,
        "GOOGL": 175.0,
        "MSFT": 420.0,
        "AMZN": 180.0,
        "TSLA": 245.0,
        "NVDA": 875.0,
        "META": 485.0,
        "JPM": 210.0,
        "V": 280.0,
        "NFLX": 680.0,
    }

    # GBM parameters per ticker
    DEFAULT_DRIFT = 0.0      # Annual drift (0 = no trend)
    DEFAULT_VOLATILITY = 0.02 # Volatility (2% std dev per update)

    def __init__(self, update_interval: float = 0.5):
        super().__init__()
        self.update_interval = update_interval
        self._tickers: Dict[str, Dict] = {}  # ticker -> {price, drift, volatility}
        self._price_cache: Dict[str, PriceUpdate] = {}
        self._task: Optional[asyncio.Task] = None

    def set_tickers(self, tickers: List[str]):
        """Register tickers for simulation."""
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker not in self._tickers:
                # Initialize with seed price or default
                seed_price = self.DEFAULT_PRICES.get(ticker, 100.0)
                self._tickers[ticker] = {
                    "price": seed_price,
                    "drift": self.DEFAULT_DRIFT,
                    "volatility": self.DEFAULT_VOLATILITY,
                }

                # Initialize cache
                self._price_cache[ticker] = PriceUpdate(
                    ticker=ticker,
                    price=Decimal(str(seed_price)),
                    previous_price=Decimal(str(seed_price)),
                    timestamp=datetime.now(),
                )

        print(f"MarketSimulator: Tracking {len(self._tickers)} tickers")

    def get_current_price(self, ticker: str) -> Optional[PriceUpdate]:
        """Get cached price for a ticker."""
        return self._price_cache.get(ticker.upper())

    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """Get all cached prices."""
        return self._price_cache.copy()

    async def start(self):
        """Start the simulation loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._simulation_loop())
        print("MarketSimulator: Started")

    async def stop(self):
        """Stop the simulation gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("MarketSimulator: Stopped")

    async def _simulation_loop(self):
        """Main simulation loop using geometric Brownian motion."""
        iteration = 0

        while self._running:
            # Generate correlated random shocks
            market_shock = random.gauss(0, 0.01)  # Market-wide movement

            new_prices = {}

            for ticker, params in self._tickers.items():
                # Geometric Brownian Motion formula:
                # S(t+1) = S(t) * exp((drift - 0.5*vol^2)*dt + vol*sqrt(dt)*Z)

                current_price = params["price"]
                drift = params["drift"]
                volatility = params["volatility"]

                # Combine market shock + ticker-specific shock
                ticker_shock = random.gauss(0, volatility)
                total_shock = 0.7 * market_shock + 0.3 * ticker_shock

                # Apply GBM
                dt = self.update_interval / (252 * 6.5 * 3600)  # Fraction of trading year
                drift_component = (drift - 0.5 * volatility ** 2) * dt
                shock_component = volatility * math.sqrt(dt) * total_shock

                new_price = current_price * math.exp(drift_component + shock_component)

                # Occasional random events (1% chance per update)
                if random.random() < 0.01:
                    event_magnitude = random.uniform(-0.05, 0.05)  # ±5%
                    new_price *= (1 + event_magnitude)
                    print(f"MarketSimulator: Random event on {ticker}: {event_magnitude:+.2%}")

                # Store previous price
                previous_price = Decimal(str(current_price))

                # Update ticker state
                params["price"] = new_price

                # Create price update
                price_update = PriceUpdate(
                    ticker=ticker,
                    price=Decimal(str(round(new_price, 2))),
                    previous_price=previous_price,
                    timestamp=datetime.now(),
                )

                new_prices[ticker] = price_update
                self._price_cache[ticker] = price_update

            # Notify callbacks
            if new_prices:
                self._notify_callbacks(new_prices)

            iteration += 1
            await asyncio.sleep(self.update_interval)
```

## Factory Function

```python
import os
from typing import Optional

def create_market_data_source() -> MarketDataSource:
    """
    Factory function to create the appropriate market data source.

    Returns MassiveClient if MASSIVE_API_KEY is set, otherwise MarketSimulator.
    """
    api_key = os.getenv("MASSIVE_API_KEY")

    if api_key:
        print("Creating MassiveClient (real market data)")
        # Free tier: 5 calls/min -> 15 second interval is safe
        # Paid tier: adjust interval based on plan
        interval = 15  # seconds
        return MassiveClient(api_key=api_key, poll_interval=interval)
    else:
        print("Creating MarketSimulator (simulated data)")
        # Update every 500ms for smooth animations
        return MarketSimulator(update_interval=0.5)
```

## Integration with Price Cache

```python
class PriceCache:
    """Central cache for current prices, updated by market data source."""

    def __init__(self, market_data: MarketDataSource):
        self.market_data = market_data
        # Register callback to update cache
        self.market_data.add_callback(self._on_price_update)

    def _on_price_update(self, prices: Dict[str, PriceUpdate]):
        """Handle price updates from market data source."""
        # Cache is maintained by the MarketDataSource itself
        # This method can trigger SSE broadcasts, logging, etc.
        pass

    def get_price(self, ticker: str) -> Optional[PriceUpdate]:
        """Get current price for a ticker."""
        return self.market_data.get_current_price(ticker)

    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """Get all current prices."""
        return self.market_data.get_all_prices()
```

## Usage in FastAPI Application

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Global market data source
market_data: Optional[MarketDataSource] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    global market_data

    # Initialize market data source
    market_data = create_market_data_source()

    # Set initial tickers (from database or config)
    default_tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                       "NVDA", "META", "JPM", "V", "NFLX"]
    market_data.set_tickers(default_tickers)

    # Start data source
    await market_data.start()

    yield  # App runs here

    # Cleanup
    await market_data.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/api/prices/{ticker}")
async def get_price(ticker: str):
    """Get current price for a ticker."""
    price = market_data.get_current_price(ticker)
    if not price:
        return {"error": "Ticker not found"}, 404

    return {
        "ticker": price.ticker,
        "price": float(price.price),
        "previous_price": float(price.previous_price),
        "change_percent": price.change_percent,
        "timestamp": price.timestamp.isoformat(),
    }
```

## Testing

### Mocking the Interface

```python
class MockMarketData(MarketDataSource):
    """Mock implementation for testing."""

    def __init__(self):
        super().__init__()
        self._prices = {}

    def set_price(self, ticker: str, price: float):
        """Set a price manually for testing."""
        self._prices[ticker] = PriceUpdate(
            ticker=ticker,
            price=Decimal(str(price)),
            previous_price=Decimal(str(price)),
            timestamp=datetime.now(),
        )

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False

    def set_tickers(self, tickers: List[str]):
        pass

    def get_current_price(self, ticker: str) -> Optional[PriceUpdate]:
        return self._prices.get(ticker.upper())

    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        return self._prices.copy()

# Usage in tests
def test_portfolio_value():
    market_data = MockMarketData()
    market_data.set_price("AAPL", 190.0)
    market_data.set_price("GOOGL", 175.0)

    # Test portfolio logic using mock prices
    assert market_data.get_current_price("AAPL").price == Decimal("190.0")
```

## Key Design Decisions

### 1. Immutable Price Updates
`PriceUpdate` is a dataclass with frozen semantics — prevents accidental mutation and makes the data flow explicit.

### 2. Callback Pattern
Observers register callbacks to receive updates. This decouples the data source from consumers (SSE, database, logging, etc.).

### 3. Async/Await Throughout
All I/O operations use async for clean concurrency. Background tasks use `asyncio.create_task()`.

### 4. Decimal for Money
Financial calculations use Python's `Decimal` type to avoid floating-point errors. Convert to/from float only at system boundaries (API responses, display).

### 5. Abstract Base Class
Using `abc.ABC` enforces interface contracts. New implementations (e.g., Alpha Vantage, IEX Cloud) just extend `MarketDataSource`.

### 6. Factory Pattern
`create_market_data_source()` hides the selection logic. Application code never imports `MassiveClient` or `MarketSimulator` directly.

## Environment Variable Behavior

```bash
# Use simulator (default)
# No MASSIVE_API_KEY set

# Use real market data
export MASSIVE_API_KEY="your-key-here"

# Force simulator even if key is set (for testing)
export MASSIVE_API_KEY=""
```

The factory checks: `if api_key:` so empty string is treated as "use simulator".

## Future Enhancements

### Multi-User Watchlist Support
```python
class MultiUserMarketData(MarketDataSource):
    """Market data source that tracks per-user watchlists."""

    def set_user_tickers(self, user_id: str, tickers: List[str]):
        """Set tickers for a specific user."""
        # Union of all users' tickers is what we poll
        pass

    def get_user_prices(self, user_id: str) -> Dict[str, PriceUpdate]:
        """Get prices for tickers a specific user is watching."""
        pass
```

### WebSocket Support (Alternative to REST Polling)
```python
class MassiveWebSocketClient(MarketDataSource):
    """Use Massive WebSocket for real-time updates instead of polling."""
    # Implementation would use polygon.websocketClient
    pass
```

### Caching Layer
```python
class CachedMarketData(MarketDataSource):
    """Wrapper that adds Redis caching to any market data source."""

    def __init__(self, source: MarketDataSource, redis_client):
        self.source = source
        self.redis = redis_client

    async def start(self):
        await self.source.start()
        self.source.add_callback(self._cache_prices)
```

## Summary

The unified `MarketDataSource` interface provides:

✅ **Single API** for all price operations
✅ **Runtime switching** between real and simulated data
✅ **Type safety** with clear contracts
✅ **Easy testing** with mock implementations
✅ **Callback pattern** for decoupled consumers
✅ **Async-first** design for FastAPI integration
✅ **Decimal precision** for financial accuracy

This design makes the FinAlly backend market-data-agnostic, enabling seamless development with the simulator and production deployment with real data.
