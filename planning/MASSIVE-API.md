# Massive API Documentation (formerly Polygon.io)

## Overview

Massive (formerly Polygon.io) provides institutional-grade market data with real-time stock quotes, trades, and historical data. This document focuses on the REST API endpoints needed for the FinAlly project.

**Key Facts:**
- Real-time data with <20ms latency
- Coverage: All US exchanges, dark pools, and OTC markets
- Free tier: 5 API calls/minute
- Authentication: API key via query parameter or header
- Base URL: `https://api.massive.com` (legacy `api.polygon.io` still supported)

## Authentication

All API requests require an API key, which can be provided in two ways:

### Query Parameter (Recommended for Testing)
```python
import requests

api_key = "YOUR_API_KEY_HERE"
ticker = "AAPL"
url = f"https://api.massive.com/v2/last/trade/{ticker}?apiKey={api_key}"
response = requests.get(url)
```

### Header-Based (Recommended for Production)
```python
import requests

api_key = "YOUR_API_KEY_HERE"
ticker = "AAPL"
url = f"https://api.massive.com/v2/last/trade/{ticker}"
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get(url, headers=headers)
```

## Python Client Library

### Installation

```bash
pip install polygon-api-client
# or with uv
uv add polygon-api-client
```

### Basic Setup

```python
from polygon import RESTClient

# Initialize client
client = RESTClient(api_key="YOUR_API_KEY_HERE")

# With debugging enabled
client = RESTClient(
    api_key="YOUR_API_KEY_HERE",
    trace=True,      # Enable request tracing
    verbose=True     # Enable verbose output
)
```

## Core Endpoints for FinAlly

### 1. Last Trade - Get Most Recent Price

**Endpoint:** `GET /v2/last/trade/{ticker}`

**Python Client:**
```python
from polygon import RESTClient

client = RESTClient(api_key="YOUR_API_KEY")

# Get last trade for a single ticker
trade = client.get_last_trade(ticker="AAPL")
print(f"Price: ${trade.price}")
print(f"Size: {trade.size} shares")
print(f"Time: {trade.sip_timestamp}")
```

**Raw REST Example:**
```python
import requests
from datetime import datetime

def get_last_trade(ticker: str, api_key: str) -> dict:
    """Get the last trade for a ticker."""
    url = f"https://api.massive.com/v2/last/trade/{ticker}"
    params = {"apiKey": api_key}

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    return {
        "ticker": ticker,
        "price": data["results"]["p"],
        "size": data["results"]["s"],
        "timestamp": datetime.fromtimestamp(data["results"]["t"] / 1000),
        "exchange": data["results"]["x"]
    }

# Usage
trade = get_last_trade("AAPL", "YOUR_API_KEY")
print(f"{trade['ticker']}: ${trade['price']} at {trade['timestamp']}")
```

**Response Format:**
```json
{
  "status": "success",
  "results": {
    "T": "AAPL",
    "p": 190.25,
    "s": 100,
    "t": 1642176000000,
    "x": 4,
    "c": [14, 37, 41]
  }
}
```

### 2. Last Quote - Get Current Bid/Ask (NBBO)

**Endpoint:** `GET /v2/last/nbbo/{ticker}`

**Python Client:**
```python
# Get last quote (National Best Bid and Offer)
quote = client.get_last_quote(ticker="AAPL")
print(f"Bid: ${quote.bid_price} x {quote.bid_size}")
print(f"Ask: ${quote.ask_price} x {quote.ask_size}")
print(f"Midpoint: ${(quote.bid_price + quote.ask_price) / 2}")
```

**Raw REST Example:**
```python
def get_last_quote(ticker: str, api_key: str) -> dict:
    """Get the last NBBO quote for a ticker."""
    url = f"https://api.massive.com/v2/last/nbbo/{ticker}"
    params = {"apiKey": api_key}

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    results = data["results"]

    return {
        "ticker": ticker,
        "bid_price": results["P"],
        "bid_size": results["S"],
        "ask_price": results["p"],
        "ask_size": results["s"],
        "timestamp": datetime.fromtimestamp(results["t"] / 1000)
    }
```

### 3. Snapshot (All Tickers) - Best for Multiple Tickers

**Endpoint:** `GET /v2/snapshot/locale/us/markets/stocks/tickers`

This is the **most efficient endpoint** for getting prices for multiple tickers in a single API call.

**Python Client:**
```python
# Get snapshot for specific tickers
tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
snapshots = client.get_snapshot_all(symbols=tickers)

for snapshot in snapshots:
    print(f"{snapshot.ticker}: ${snapshot.day.c} ({snapshot.day.change_percent:+.2f}%)")
```

**Raw REST Example:**
```python
def get_snapshot_multiple(tickers: list[str], api_key: str) -> dict[str, dict]:
    """Get snapshot data for multiple tickers in one API call."""
    url = "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers"
    params = {
        "apiKey": api_key,
        "tickers": ",".join(tickers)  # Comma-separated list
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    results = {}

    for snapshot in data.get("tickers", []):
        ticker = snapshot["ticker"]
        results[ticker] = {
            "ticker": ticker,
            "price": snapshot["day"]["c"],        # Close price
            "open": snapshot["day"]["o"],
            "high": snapshot["day"]["h"],
            "low": snapshot["day"]["l"],
            "volume": snapshot["day"]["v"],
            "previous_close": snapshot["prevDay"]["c"],
            "change_percent": ((snapshot["day"]["c"] - snapshot["prevDay"]["c"])
                             / snapshot["prevDay"]["c"] * 100),
            "last_trade_price": snapshot.get("lastTrade", {}).get("p"),
            "last_trade_time": snapshot.get("lastTrade", {}).get("t"),
            "updated_at": datetime.fromtimestamp(snapshot["updated"] / 1000000000)
        }

    return results

# Usage
tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
prices = get_snapshot_multiple(tickers, "YOUR_API_KEY")

for ticker, data in prices.items():
    print(f"{ticker}: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")
```

**Response Format:**
```json
{
  "status": "OK",
  "count": 10,
  "tickers": [
    {
      "ticker": "AAPL",
      "day": {
        "c": 190.25,
        "h": 192.50,
        "l": 189.00,
        "o": 189.50,
        "v": 75000000,
        "vw": 190.15
      },
      "prevDay": {
        "c": 189.50,
        "h": 191.00,
        "l": 188.75,
        "o": 190.00,
        "v": 65000000
      },
      "lastTrade": {
        "p": 190.25,
        "s": 100,
        "t": 1642176000000,
        "x": 4
      },
      "updated": 1642176000000000000
    }
  ]
}
```

### 4. Aggregates (Bars) - Historical Data

**Endpoint:** `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`

**Python Client:**
```python
from polygon.rest.models import GetStocksAggregatesTimespanEnum

# Get daily aggregates for date range
aggs = client.get_stocks_aggregates(
    ticker="AAPL",
    multiplier=1,
    timespan=GetStocksAggregatesTimespanEnum.Day,
    from_="2024-01-01",
    to="2024-01-31"
)

for bar in aggs:
    print(f"{bar.timestamp}: O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}")
```

## Rate Limits

### Free Tier
- **5 API calls per minute**
- Suitable for development and testing
- Real-time data with 15-minute delay (upgrade required for live)

### Paid Tiers
Paid plans offer higher rate limits and real-time data access. Rate limits vary by plan:
- **Starter:** Higher limits for small production apps
- **Developer:** Increased limits for active trading apps
- **Advanced:** Institutional-grade limits for high-frequency use

For current pricing and exact limits, visit [Massive Pricing](https://massive.com/pricing).

### Rate Limit Handling

```python
import time
from requests.exceptions import HTTPError

def rate_limited_request(func, *args, max_retries=3, **kwargs):
    """Wrapper to handle rate limiting with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded for rate-limited request")

# Usage
try:
    trade = rate_limited_request(client.get_last_trade, ticker="AAPL")
except Exception as e:
    print(f"Failed to fetch data: {e}")
```

## Polling Strategy for FinAlly

Based on rate limits, recommended polling intervals:

### Free Tier (5 calls/min)
```python
# Poll 10 tickers using snapshot endpoint
# 1 call per batch of tickers
# Safe interval: 15 seconds (4 calls/min)

import asyncio
from datetime import datetime

async def poll_prices_free_tier(tickers: list[str], api_key: str):
    """Poll prices for multiple tickers respecting free tier limits."""
    interval = 15  # seconds between polls (4 calls/min)

    while True:
        try:
            print(f"[{datetime.now()}] Polling {len(tickers)} tickers...")
            prices = get_snapshot_multiple(tickers, api_key)

            # Process prices (update cache, broadcast via SSE, etc.)
            for ticker, data in prices.items():
                print(f"  {ticker}: ${data['price']:.2f}")

        except Exception as e:
            print(f"Error polling prices: {e}")

        await asyncio.sleep(interval)
```

### Paid Tier (Higher Limits)
```python
# Poll more frequently based on your plan's limits
# Example: Developer tier with 100 calls/min
# Safe interval: 2-5 seconds

async def poll_prices_paid_tier(tickers: list[str], api_key: str):
    """Poll prices with higher frequency for paid tiers."""
    interval = 2  # seconds between polls (30 calls/min - safe margin)

    while True:
        try:
            prices = get_snapshot_multiple(tickers, api_key)
            # Process and broadcast prices
        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(interval)
```

## Error Handling

```python
from requests.exceptions import HTTPError, Timeout, ConnectionError

def safe_api_call(func, *args, **kwargs):
    """Safe wrapper for API calls with comprehensive error handling."""
    try:
        return func(*args, **kwargs)

    except HTTPError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid API key")
        elif e.response.status_code == 403:
            raise ValueError("API key lacks required permissions")
        elif e.response.status_code == 404:
            raise ValueError("Ticker not found")
        elif e.response.status_code == 429:
            raise ValueError("Rate limit exceeded")
        else:
            raise ValueError(f"API error: {e.response.status_code}")

    except Timeout:
        raise ValueError("API request timed out")

    except ConnectionError:
        raise ValueError("Failed to connect to API")

    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")
```

## Complete Example: Polling Service

```python
import asyncio
from typing import Dict, List, Callable
from datetime import datetime
from polygon import RESTClient

class MassivePricePoller:
    """Service to poll Massive API and update price cache."""

    def __init__(self, api_key: str, interval: int = 15):
        self.client = RESTClient(api_key=api_key)
        self.interval = interval
        self.running = False
        self.tickers: List[str] = []
        self.callbacks: List[Callable] = []

    def set_tickers(self, tickers: List[str]):
        """Update the list of tickers to poll."""
        self.tickers = list(set(tickers))  # Remove duplicates
        print(f"Polling {len(self.tickers)} tickers: {', '.join(self.tickers)}")

    def add_callback(self, callback: Callable[[Dict], None]):
        """Register a callback to receive price updates."""
        self.callbacks.append(callback)

    async def start(self):
        """Start polling loop."""
        self.running = True
        print(f"Starting price poller (interval: {self.interval}s)")

        while self.running:
            if not self.tickers:
                await asyncio.sleep(self.interval)
                continue

            try:
                # Get snapshot for all tickers in one API call
                snapshots = self.client.get_snapshot_all(symbols=self.tickers)

                prices = {}
                for snapshot in snapshots:
                    prices[snapshot.ticker] = {
                        "ticker": snapshot.ticker,
                        "price": snapshot.day.c,
                        "previous_price": snapshot.prev_day.c,
                        "timestamp": datetime.now(),
                        "volume": snapshot.day.v,
                        "change_percent": snapshot.day.change_percent
                    }

                # Notify all callbacks
                for callback in self.callbacks:
                    callback(prices)

                print(f"[{datetime.now()}] Polled {len(prices)} prices")

            except Exception as e:
                print(f"Error polling prices: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop polling loop."""
        self.running = False
        print("Stopping price poller")

# Usage example
async def main():
    poller = MassivePricePoller(api_key="YOUR_API_KEY", interval=15)

    # Set tickers to poll
    poller.set_tickers(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"])

    # Register callback to handle price updates
    def on_price_update(prices: Dict):
        for ticker, data in prices.items():
            print(f"  {ticker}: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")

    poller.add_callback(on_price_update)

    # Start polling
    await poller.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## References

- [Massive Official Documentation](https://massive.com/docs)
- [Python Client Library](https://github.com/polygon-io/client-python)
- [Rate Limits Documentation](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis)
- [Pricing Plans](https://massive.com/pricing)
- [Stocks API Overview](https://polygon.readthedocs.io/en/latest/Stocks.html)

## Key Takeaways for FinAlly

1. **Use Snapshot Endpoint:** Most efficient for getting prices for 10 default tickers in one API call
2. **Free Tier Polling:** 15-second intervals (4 calls/min) provides good balance of freshness and safety margin
3. **Paid Tier Polling:** 2-5 second intervals depending on plan limits
4. **Error Handling:** Always wrap API calls with retry logic and rate limit handling
5. **Authentication:** Store API key in environment variable, never commit to repo
6. **Fallback:** Always have simulator as fallback when API key is not provided
