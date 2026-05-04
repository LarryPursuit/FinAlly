# FinAlly — Project Status Summary

**Last updated:** 2026-04-28

## Overview

FinAlly (Finance Ally) is an AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades. It targets a modern Bloomberg-terminal aesthetic with an AI copilot.

**Architecture:** Single Docker container on port 8000 — FastAPI backend serving a static Next.js export, SQLite database, SSE streaming, and LLM integration via OpenRouter/Cerebras.

## Completion Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Backend Core | **Complete** | Database, API routes, services, background tasks, market data |
| Phase 2: LLM/Chat | **Complete** | LLM client abstraction, chat orchestration, auto-execute trades |
| Phase 3: Frontend | Not started | Next.js static export with trading UI |
| Phase 4: Docker & E2E | Not started | Multi-stage Dockerfile, Playwright E2E tests |

## Current Metrics

- **232 tests**, all passing
- **90% code coverage**
- **~2,514 lines** of application code (29 files)
- **~2,262 lines** of test code (25 files)
- **0 lint errors** (ruff)

---

## Phase 1: Backend Core (Complete)

### Database Layer (`app/db/`)

SQLite with lazy initialization — creates schema and seeds data on first run.

| Table | Purpose |
|-------|---------|
| `users_profile` | User state, cash balance (default $10,000) |
| `watchlist` | Tracked tickers (default: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) |
| `positions` | Current holdings (one row per ticker per user) |
| `trades` | Append-only trade history |
| `portfolio_snapshots` | Portfolio value over time (recorded every 30s + after trades) |
| `chat_messages` | Conversation history with LLM (role, content, actions JSON) |

Key: All tables use `user_id` defaulting to `"default"` for future multi-user support. Financial calculations use Python `Decimal`.

**Files:** `database.py` (396 lines), `models.py` (126), `schema.py` (61), `seed.py` (17)

### API Routes (`app/routes/`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/portfolio` | GET | Positions, cash balance, total value, unrealized P&L |
| `/api/portfolio/trade` | POST | Execute trade: `{ticker, quantity, side}` |
| `/api/portfolio/history` | GET | Portfolio value snapshots for P&L chart |
| `/api/watchlist` | GET | Watchlist tickers with latest prices |
| `/api/watchlist` | POST | Add ticker |
| `/api/watchlist/{ticker}` | DELETE | Remove ticker |
| `/api/chat` | POST | Send message, receive response + executed actions |
| `/api/health` | GET | Health check |
| `/api/stream/prices` | GET | SSE stream of live price updates |

**Files:** `portfolio.py` (95), `watchlist.py` (112), `chat.py` (54), `health.py` (27)

### Services (`app/services/`)

- **Trading** (`trading.py`, 168 lines) — `execute_trade()` with atomic DB transactions, cash/position validation, concurrent-trade serialization via `asyncio.Lock`
- **Portfolio** (`portfolio.py`, 74 lines) — `get_portfolio_summary()` and `compute_total_value()` using live prices from PriceCache
- **Input Validation** (`validation.py`, 47 lines) — `validate_ticker()` (1-5 chars, `[A-Z0-9.-]`), `validate_quantity()`, `validate_side()`

### Background Tasks (`app/tasks/`)

- **Portfolio snapshots** — Records total portfolio value every 30s
- **Snapshot cleanup** — Daily pruning of snapshots older than retention period

**File:** `snapshots.py` (58 lines)

### Market Data (`app/market/`)

Complete market data subsystem with two interchangeable implementations behind a Strategy pattern.

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM with Cholesky-correlated moves (default)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        v
   PriceCache (thread-safe, in-memory, version counter for SSE)
        │
        ├──> SSE stream (/api/stream/prices)
        ├──> Portfolio valuation
        └──> Trade execution
```

Key design decisions:
- GBM with sector-correlated moves (Cholesky decomposition) — tech stocks correlate at 0.6, finance at 0.5, cross-sector at 0.3
- Random shock events (~0.1% chance per tick) for visual drama
- PriceCache as single point of truth with monotonic version counter
- SSE over WebSockets — simpler, one-way push

**Files:** `simulator.py` (270), `massive_client.py` (128), `cache.py` (75), `stream.py` (87), `interface.py` (57), `models.py` (49), `seed_prices.py` (47), `factory.py` (31)

### App Entrypoint (`app/main.py`, 93 lines)

FastAPI lifespan manages startup/shutdown of all subsystems: database initialization, market data source, background tasks, and router mounting.

---

## Phase 2: LLM/Chat Integration (Complete)

### LLM Client (`app/services/llm.py`, 171 lines)

ABC-based abstraction with three implementations:

| Client | Purpose |
|--------|---------|
| `OpenRouterClient` | Production — LiteLLM → OpenRouter → Cerebras (`openrouter/openai/gpt-oss-120b`), structured outputs via Pydantic |
| `MockLLMClient` | Testing/dev — deterministic pattern-matched responses (buy/sell/add/remove patterns) |
| `create_llm_client()` | Factory — reads `LLM_MOCK` and `OPENROUTER_API_KEY` env vars |

Structured output schema (Pydantic):
```python
class LLMResponse(BaseModel):
    message: str                                    # Conversational text
    trades: list[TradeAction] = []                  # Auto-execute trades
    watchlist_changes: list[WatchlistAction] = []   # Auto-execute watchlist changes
```

### Chat Orchestration (`app/services/chat.py`, 207 lines)

`process_chat_message()` flow:
1. Build portfolio context string (cash, positions, watchlist, total value)
2. Load + trim message history (~4000 token budget, max 25 messages)
3. Construct system prompt + context + history + user message
4. Call LLM client
5. Auto-execute trades (best-effort, continues on failure)
6. Auto-execute watchlist changes (best-effort)
7. Store messages + actions JSON in database
8. Return structured response

### Chat Route (`app/routes/chat.py`, 54 lines)

`POST /api/chat` with Pydantic validation (`min_length=1`), LLM error handling (500 with `LLM_ERROR` code).

---

## Test Suite Breakdown

| Area | Tests | Key Coverage |
|------|-------|-------------|
| Market data (models, cache, simulator, factory, massive) | 73 | Simulator: 98%, Cache/Models/Factory: 100% |
| Database | 25 | Schema, CRUD, constraints, chat messages |
| Data models | 14 | All Pydantic/dataclass models |
| Validation | 22 | Ticker, quantity, side validators |
| Services (trading, portfolio) | 20 | Trade execution, P&L, concurrency |
| Services (LLM, chat) | 37 | Pydantic models, mock client, chat flow, context/history |
| Routes (portfolio, watchlist, health) | 18 | HTTP layer, error codes, response shapes |
| Routes (chat) | 8 | POST /api/chat, LLM errors, trade-through-route |
| Background tasks | 4 | Snapshot recording, cleanup |
| **Total** | **232** | **90% coverage** |

---

## Environment Variables

```bash
OPENROUTER_API_KEY=...    # Required for LLM chat (OpenRouter API key)
MASSIVE_API_KEY=          # Optional: Polygon.io key for real market data (simulator used if empty)
LLM_MOCK=false            # Optional: "true" for deterministic mock responses (testing/dev)
```

---

## What Remains

### Phase 3: Frontend (Next.js Static Export)

- Watchlist panel with live-updating prices (SSE), sparklines, price flash animations
- Main chart area (selected ticker, built from SSE data since page load)
- Portfolio heatmap (treemap by weight, colored by P&L)
- P&L chart (line chart from portfolio_snapshots)
- Positions table
- Trade bar (ticker, quantity, buy/sell buttons)
- AI chat panel (message input, conversation history, inline trade confirmations)
- Header with live portfolio value, cash balance, connection status indicator
- Dark theme (`#0d1117`), accent yellow (`#ecad0a`), blue (`#209dd7`), purple (`#753991`)

### Phase 4: Docker & Deployment

- Multi-stage Dockerfile (Node build → Python runtime)
- Static frontend served by FastAPI
- Volume-mounted SQLite at `/app/db`
- Start/stop scripts for macOS/Linux/Windows

### Phase 5: E2E Tests (Playwright)

- Separate `docker-compose.test.yml` with Playwright container
- Tests run with `LLM_MOCK=true`
- Key scenarios: fresh start, watchlist CRUD, buy/sell, portfolio visualization, AI chat, SSE resilience

---

## Key Architectural Decisions

1. **Single container, single port** — No CORS, no service orchestration, one Docker command to run
2. **SSE over WebSockets** — One-way push is sufficient; simpler, universal browser support
3. **SQLite with lazy init** — No migration step, no database server, auto-seeds on first run
4. **Strategy pattern for market data** — Simulator and Massive API share an ABC; downstream code is source-agnostic
5. **ABC pattern for LLM** — OpenRouter and Mock clients share an interface; enables testing without API keys
6. **Auto-execute trades from LLM** — No confirmation dialog; simulated environment with fake money makes this safe and impressive
7. **Best-effort execution** — Multiple trades/watchlist changes execute in order; failures collected, not short-circuited
8. **Structured outputs** — Pydantic models for LLM response parsing; type-safe trade/watchlist actions
9. **Decimal precision** — Python `Decimal` for all financial calculations; floats only in GBM simulator

---

## File Reference

### Backend Application (`backend/app/`)

```
app/
├── __init__.py
├── main.py              (93)   App entrypoint, lifespan, router mounting
├── validation.py        (47)   Input validators (ticker, quantity, side)
├── db/
│   ├── database.py      (396)  Database class, all CRUD operations
│   ├── models.py        (126)  Pydantic/dataclass models
│   ├── schema.py        (61)   SQL schema definitions
│   └── seed.py          (17)   Default seed data
├── market/
│   ├── simulator.py     (270)  GBM simulator + SimulatorDataSource
│   ├── massive_client.py(128)  Polygon.io REST client
│   ├── stream.py        (87)   SSE endpoint factory
│   ├── cache.py         (75)   Thread-safe PriceCache
│   ├── interface.py     (57)   MarketDataSource ABC
│   ├── models.py        (49)   PriceUpdate dataclass
│   ├── seed_prices.py   (47)   Seed prices, GBM params, correlation groups
│   └── factory.py       (31)   create_market_data_source()
├── routes/
│   ├── watchlist.py     (112)  Watchlist CRUD endpoints
│   ├── portfolio.py     (95)   Portfolio + trade endpoints
│   ├── chat.py          (54)   POST /api/chat
│   └── health.py        (27)   GET /api/health
├── services/
│   ├── chat.py          (207)  Chat orchestration, context, history
│   ├── llm.py           (171)  LLM client ABC, OpenRouter, Mock, factory
│   ├── trading.py       (168)  Trade execution, validation, locking
│   └── portfolio.py     (74)   Portfolio summary, total value
└── tasks/
    └── snapshots.py     (58)   Background snapshot + cleanup tasks
```

### Backend Tests (`backend/tests/`)

```
tests/
├── conftest.py          (44)   Shared fixtures (db, price_cache)
├── test_validation.py   (85)   Validation tests
├── db/                         Database + model tests (308 lines)
├── market/                     Market data tests (729 lines)
├── routes/                     Route/HTTP tests (439 lines)
├── services/                   Service tests (608 lines)
└── tasks/                      Background task tests (43 lines)
```

---

## Planning Documents

| Document | Status | Location |
|----------|--------|----------|
| `PLAN.md` | **Active** — Master project specification | `planning/` |
| `MARKET_DATA_SUMMARY.md` | **Active** — Concise market data summary | `planning/` |
| `Summarized.md` | **Active** — This document | `planning/` |
| `MARKET_DATA_DESIGN.md` | Archived — Detailed market data design | `planning/archive/` |
| `MARKET_INTERFACE.md` | Archived — Interface design | `planning/archive/` |
| `MARKET_SIMULATOR.md` | Archived — Simulator design | `planning/archive/` |
| `MASSIVE-API.md` | Archived — Polygon.io API docs | `planning/archive/` |
| `MARKET_DATA_REVIEW.md` | Archived — Code review notes | `planning/archive/` |
