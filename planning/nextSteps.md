# FinAlly — Next Steps & Code Review

_Generated: 2026-04-24_

---

## What Has Been Built

### Market Data Subsystem — Complete ✅

The only completed component is `backend/app/market/` (8 modules, ~500 lines):

| Module | Purpose | Status |
|---|---|---|
| `models.py` | `PriceUpdate` — frozen dataclass with change/direction computed properties | ✅ |
| `interface.py` | `MarketDataSource` — abstract base class | ✅ |
| `cache.py` | `PriceCache` — thread-safe in-memory price store | ✅ |
| `seed_prices.py` | Realistic seed prices, per-ticker GBM params, correlation constants | ✅ |
| `simulator.py` | `GBMSimulator` (Cholesky-correlated GBM) + `SimulatorDataSource` | ✅ |
| `massive_client.py` | `MassiveDataSource` — Polygon.io REST polling client | ✅ |
| `factory.py` | `create_market_data_source()` — env-driven factory | ✅ |
| `stream.py` | FastAPI SSE endpoint factory | ✅ |

**Tests:** 73 tests across 6 modules, 84% overall coverage. All passing.

**Demo:** `backend/market_data_demo.py` — Rich terminal live-price dashboard.

---

## What Is Missing (Entire Remainder of the Platform)

The following major components have **not been started**:

| Component | Priority | Notes |
|---|---|---|
| `backend/app/main.py` (FastAPI entry point) | 🔴 Critical | No application wiring exists |
| Database schema + lazy initialization | 🔴 Critical | No `db/` or schema SQL |
| Portfolio API endpoints | 🔴 Critical | `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history` |
| Watchlist API endpoints | 🔴 Critical | `/api/watchlist` CRUD |
| Trade execution engine | 🔴 Critical | Cash/position validation, atomic writes |
| Background tasks (snapshots, cleanup) | 🔴 Critical | Portfolio snapshot every 30s, retention cleanup |
| Health check endpoint | 🔴 Critical | `/api/health` |
| LLM chat integration | 🟡 High | `/api/chat`, LiteLLM → OpenRouter, structured outputs |
| Frontend (Next.js) | 🟡 High | Entire `frontend/` directory missing |
| Dockerfile (multi-stage) | 🟡 High | No build/deployment config |
| `.env.example` | 🟡 High | README references it; file doesn't exist |
| `scripts/` (start/stop) | 🟠 Medium | No shell/PowerShell launch scripts |
| `docker-compose.yml` | 🟠 Medium | Convenience wrapper |
| E2E tests (`test/`) | 🟠 Medium | Playwright + docker-compose.test.yml |

---

## Code Review: Market Data Subsystem

### Strengths

1. **Clean Strategy pattern** — `SimulatorDataSource` and `MassiveDataSource` both implement `MarketDataSource`. Downstream code is source-agnostic. Easy to add a third data source in the future.

2. **Well-tested** — 73 tests at 84% coverage. Edge cases covered: empty tickers, double-stop, malformed snapshots, idempotent operations, disconnect detection, concurrency resilience.

3. **GBM implementation is solid** — Cholesky decomposition for correlated moves is correct. The `TRADING_SECONDS_PER_YEAR` constant is documented with the exact math. `math.exp(drift + diffusion)` guarantees prices stay positive.

4. **Version-based SSE change detection** — Using `PriceCache.version` counter to detect new data before emitting is efficient and avoids sending duplicate events.

5. **Sync-in-thread pattern for Massive** — `await asyncio.to_thread(self._fetch_snapshots)` correctly avoids blocking the event loop with a synchronous REST client.

6. **Clean public API surface** — `backend/app/market/__init__.py` explicitly lists `__all__`, and `backend/CLAUDE.md` documents usage clearly.

---

### Issues Found

#### Issue 1 — `stream.py`: Router singleton breaks factory pattern
**File:** `backend/app/market/stream.py`, lines 17 and 20–48  
**Severity:** Medium  

```python
# Line 17 — module-level global router
router = APIRouter(prefix="/api/stream", tags=["streaming"])

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    @router.get("/prices")           # Attaches to module-level global
    async def stream_prices(...):
        ...
    return router                    # Returns the same global every time
```

If `create_stream_router()` is called more than once (e.g., in tests), the `@router.get("/prices")` decorator runs again, silently registering the same route a second time on the same router. This leads to duplicate route warnings in FastAPI.

**Fix:** Move `router = APIRouter(...)` inside the factory function so each call creates a fresh router.

---

#### Issue 2 — `stream.py`: No heartbeat/ping
**File:** `backend/app/market/stream.py`, `_generate_events()` function  
**Severity:** Medium  

The SSE generator has no heartbeat. The spec (PLAN.md §6) explicitly calls for `: ping\n\n` every 15–30 seconds. Without it, load balancers and proxies (nginx, AWS ALB, Cloudflare) will close idle connections when no event has been sent.

**Fix:** Add a periodic ping comment in `_generate_events`:
```python
last_ping = time.time()
while True:
    if time.time() - last_ping > 30:
        yield ": ping\n\n"
        last_ping = time.time()
    ...
```

---

#### Issue 3 — `stream.py`: Streams entire cache, not user's watchlist
**File:** `backend/app/market/stream.py`, lines 79–83  
**Severity:** Low (by design for now, but needs attention at integration)  

The current SSE endpoint streams all prices in `PriceCache.get_all()` regardless of the user's watchlist. The spec says: _"Server pushes price updates for the default user's watchlist tickers."_

This is acceptable at the market data layer (it has no DB access), but when `main.py` is built, the SSE generator will need either:
- A way to be given a watchlist filter, OR
- The price cache itself should only contain watchlist tickers (the simulator already supports `add_ticker`/`remove_ticker` dynamic management)

The cleanest solution is to keep the cache scoped to watchlist tickers by always calling `source.add_ticker/remove_ticker` when the watchlist changes. Since the SSE already streams everything in cache, and the cache will only have watchlist tickers, this naturally gives the correct behavior.

---

#### Issue 4 — `seed_prices.py`: Default volatility disagrees with PLAN.md
**File:** `backend/app/market/seed_prices.py`, line 34  
**Severity:** Low  

```python
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}
```

PLAN.md §6 states new tickers should get `drift=0.0, volatility=0.02`. The implementation uses `sigma=0.25` (which is 12.5x higher) and `mu=0.05`. While `0.25` annualized volatility is realistic for a stock, it contradicts the documented spec and will cause newly-added tickers to move much more aggressively than intended.

**Fix:** Align with spec (`sigma=0.02, mu=0.0`) **or** update PLAN.md to reflect the more realistic values. The latter is preferable — `0.02` is too tame; `0.25` is reasonable.

---

#### Issue 5 — `simulator.py`: New ticker gets random price instead of $100.00
**File:** `backend/app/market/simulator.py`, line 151  
**Severity:** Low  

```python
self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
```

PLAN.md §6 says: _"register it with default GBM parameters (drift=0.0, volatility=0.02, starting price=$100.00)"_. The implementation uses `random.uniform(50.0, 300.0)` instead of a fixed $100.00.

Randomizing is arguably more realistic, but it's a spec deviation. Worse, with a random seed price the behavior is non-deterministic in tests.

**Fix:** Replace with `100.00` fixed value, or document in PLAN.md that the starting price is randomized.

---

#### Issue 6 — `conftest.py`: Unused `event_loop_policy` fixture
**File:** `backend/tests/conftest.py`  
**Severity:** Minor  

```python
@pytest.fixture
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
```

This fixture is defined but never explicitly requested by any test. `pytest-asyncio` in `asyncio_mode = "auto"` handles event loop creation automatically. The fixture is dead code that adds confusion.

**Fix:** Remove it, or if needed, use `pytest_configure` hook pattern.

---

#### Issue 7 — Tests access private internals
**Files:** `test_simulator.py` lines 83, 84; `test_factory.py` lines 59, 69, 74, 79  
**Severity:** Minor  

Several tests access private attributes (`_cholesky`, `_api_key`, `_cache`, `_task`). This creates coupling to implementation details that could break if the internal naming changes.

This is common in Python and acceptable for unit tests, but worth noting as technical debt.

---

#### Issue 8 — `pyproject.toml`: Missing runtime dependencies for full app
**File:** `backend/pyproject.toml`  
**Severity:** Low (doesn't affect current market data layer, but will block next phase)  

The `pyproject.toml` only lists market-data dependencies. The full backend will also need:
- `python-dotenv` — for loading `.env` (README says `cp .env.example .env`)
- `aiosqlite` — for async SQLite access
- `pydantic` — for request/response model validation (FastAPI uses this)
- `litellm` — for LLM integration
- `httpx` — for async HTTP in tests

---

## Recommended Next Build Order

The following sequence minimizes blocked work and matches the PLAN.md §14 development workflow:

### Phase 1 — Backend Foundation (Blocking Everything Else)

**1.1 — FastAPI Application Entry Point**
- Create `backend/app/main.py` with:
  - `app = FastAPI(...)` instance
  - Startup/shutdown lifecycle events
  - Include the market stream router
  - Serve static files from `frontend/out/`
  - Logging configuration (JSON structured)

**1.2 — Database Layer**
- Create `backend/app/db/schema.sql` with all 5 tables + indexes + CHECK constraints
- Create `backend/app/db/init.py` with lazy initialization + seed data function
- Add `aiosqlite` to `pyproject.toml` dependencies
- Tables: `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`

**1.3 — Core API Routes (no LLM yet)**
- `backend/app/routes/portfolio.py` — GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
- `backend/app/routes/watchlist.py` — GET, POST, DELETE /api/watchlist/{ticker}
- `backend/app/routes/health.py` — GET /api/health

**1.4 — Background Tasks**
- Portfolio snapshot task (every 30 seconds)
- Snapshot cleanup/retention task (daily prune)

**1.5 — Trade Execution Engine**
- `asyncio.Lock` serialization for concurrent trade protection
- `Decimal` arithmetic for cash and P&L calculations
- Ticker validation (format + simulator registration)

### Phase 2 — LLM Chat Integration

**2.1 — Structured Output Schema**
- Define Pydantic model for LLM response: `message`, `trades[]`, `watchlist_changes[]`
- System prompt template with portfolio context injection

**2.2 — Chat Endpoint**
- POST /api/chat implementation
- Portfolio context builder (cash, positions + live prices, watchlist)
- Message history retrieval (last 20 messages, ~4000 token cap)
- LiteLLM → OpenRouter call (using cerebras skill)
- Auto-execute trades and watchlist changes from LLM response
- Store message + actions in `chat_messages`

**2.3 — LLM Mock Mode**
- When `LLM_MOCK=true`, return deterministic fixture response
- Required for E2E test speed and CI

### Phase 3 — Frontend

**3.1 — Project Setup**
- Next.js 14+ with TypeScript, static export (`output: 'export'`)
- Tailwind CSS with dark theme (`#0d1117` backgrounds, `#ecad0a` accent)
- React Context for: prices (SSE), portfolio (API), watchlist (API), chat (API)

**3.2 — Core Components**
- Header (portfolio total, cash balance, connection status dot)
- Watchlist panel (ticker grid with price flash + sparklines from SSE)
- Trade bar (ticker input, quantity, buy/sell buttons)
- Positions table (ticker, qty, avg cost, current price, P&L, % change)

**3.3 — Visualizations**
- Lightweight Charts (or Recharts) for main ticker chart (from SSE data)
- Portfolio heatmap/treemap (sized by weight, colored by P&L)
- P&L line chart (from `/api/portfolio/history`)

**3.4 — AI Chat Panel**
- Docked sidebar with message history
- Loading indicator during LLM call
- Trade execution confirmations inline

### Phase 4 — Docker & Deployment

**4.1 — Dockerfile**
- Stage 1: Node 20 (build Next.js static export)
- Stage 2: Python 3.12 slim + uv (copy frontend build + backend)
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**4.2 — Supporting Files**
- `.env.example` (OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK)
- `docker-compose.yml` (convenience wrapper with volume)
- `scripts/start_mac.sh`, `scripts/stop_mac.sh`
- `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`

### Phase 5 — Testing

**5.1 — Backend Unit Tests**
- Portfolio routes: trade validation, P&L math, insufficient cash/shares
- DB initialization: schema created, seed data inserted
- Chat: LLM mock responses, structured output parsing, auto-execution

**5.2 — E2E Tests (Playwright)**
- Create `test/docker-compose.test.yml`
- Test: fresh start, add/remove watchlist, buy/sell shares, portfolio heatmap, AI chat (mocked)

---

## Spec Issues to Resolve Before Phase 1

These inconsistencies in PLAN.md should be settled before building:

| # | Location | Issue | Recommended Resolution |
|---|---|---|---|
| 1 | §6 + seed_prices.py | Default volatility: PLAN says 0.02, code uses 0.25 | Update PLAN to 0.25 (more realistic) |
| 2 | §6 + simulator.py | Default start price: PLAN says $100, code uses random | Update PLAN to accept random $50–$300 or fix code to $100 |
| 3 | §7 positions.quantity | Fractional vs integer shares — PLAN is ambiguous (REAL column, but simplification suggests INTEGER) | Decide: integer only (simpler) or fractional (keeps REAL column) |
| 4 | §9 LLM model | `openrouter/openai/gpt-oss-120b` — verify model still available on OpenRouter | Confirm model ID; add fallback |
| 5 | §11 Dockerfile | Plan shows `frontend/out/` copied to `static/` but static file serving path must match | Document exact static dir convention in backend CLAUDE.md |

---

## Quick Wins (Low Effort, High Value)

These improvements to the existing code can be done independently:

1. **Add `.env.example`** — unblocks onboarding. Contents: `OPENROUTER_API_KEY=`, `MASSIVE_API_KEY=`, `LLM_MOCK=false`
2. **Fix stream.py router pattern** — move `router = APIRouter()` inside factory
3. **Add SSE heartbeat** — `: ping\n\n` every 30s in `_generate_events`
4. **Remove dead `conftest.py` fixture** — `event_loop_policy` is never used
5. **Align DEFAULT_PARAMS with spec** — pick one volatility value and document it
6. **Add missing deps to pyproject.toml** — `python-dotenv`, `aiosqlite`, `pydantic`, `litellm`

---

## Architecture Decisions Needed

Before the LLM integration is built, decide:

1. **Trade serialization:** `asyncio.Lock` per user (simple) or `BEGIN IMMEDIATE` SQLite transaction (safer against race conditions at DB level)? Recommendation: SQLite `BEGIN IMMEDIATE` — it's the authoritative source of truth.

2. **Fractional shares:** Integer-only (simpler, clear UX) or fractional (REAL column already in schema)? Recommendation: Integer-only for v1 to eliminate display/validation complexity.

3. **Portfolio history pagination:** Return all snapshots or last N? Recommendation: Last 500 snapshots (covers ~4 hours at 30s resolution), with query param `?limit=N` for flexibility.

4. **Watchlist SSE filtering:** Keep price cache = watchlist tickers (source.add_ticker/remove_ticker on watchlist changes) vs filter at SSE emit time. Recommendation: Cache = watchlist tickers (already supported by the market data layer).

5. **LLM error handling:** If OpenRouter is down, should the chat endpoint fail hard or return a degraded response? Recommendation: Return HTTP 503 with `{"error": "LLM service unavailable", "code": "LLM_ERROR"}`.
