# FinAlly — AI Trading Workstation

## 1. Vision

FinAlly (Finance Ally) is an AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades. It looks and feels like a modern Bloomberg terminal with an AI copilot.

Capstone project for an agentic AI coding course — built entirely by orchestrated coding agents. Agents coordinate through files in `planning/`.

## 2. User Experience

**First Launch:** User runs a Docker command or start script. Browser opens to `http://localhost:8000`. No login. They see a watchlist of 10 tickers with live prices, $10,000 virtual cash, a dark trading terminal UI, and an AI chat panel.

**Core Features:**
- **Live prices** — green/red flash animations on uptick/downtick (~500ms CSS fade)
- **Sparkline mini-charts** — built from SSE events since page load (no historical backend), fill progressively
- **Ticker detail chart** — click a ticker for larger view (also from SSE data since load)
- **Trading** — market orders only, instant fill at current price, no fees, no confirmation
- **Portfolio heatmap** — treemap sized by weight, colored by P&L
- **P&L chart** — total portfolio value over time from `portfolio_snapshots`
- **Positions table** — ticker, quantity, avg cost, current price, unrealized P&L, % change
- **AI chat** — natural language portfolio analysis, trade execution, watchlist management
- **Watchlist management** — add/remove tickers manually or via AI

**Visual Design:**
- Dark theme: `#0d1117` / `#1a1a2e`, muted gray borders, no pure black
- Colors: Yellow accent `#ecad0a`, Blue primary `#209dd7`, Purple secondary `#753991`
- Connection status dot: green/yellow/red in header
- Desktop-first, Bloomberg-inspired, data-dense layout

## 3. Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static files (Next.js)     │
│  SQLite (volume-mounted) + background tasks     │
└─────────────────────────────────────────────────┘
```

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Frontend | Next.js static export | Single origin, no CORS, one port |
| Backend | FastAPI + uv | Fast, modern Python project management |
| Database | SQLite | Single-user, zero config, self-contained |
| Real-time | SSE (not WebSocket) | One-way push, simpler, universal support |
| AI | LiteLLM → OpenRouter (Cerebras) | Fast inference, structured outputs |
| Market data | Simulator default, Polygon.io optional | Env-var driven, same interface |
| Deployment | Single Docker container | One command to run |
| Orders | Market orders only | No order book complexity |

## 4. Directory Structure

```
finally/
├── frontend/              # Next.js TypeScript (static export)
├── backend/               # FastAPI uv project
│   └── db/                # Schema SQL, seed data
├── planning/              # Agent coordination docs
├── scripts/               # start/stop scripts (mac + windows)
├── test/                  # Playwright E2E + docker-compose.test.yml
├── db/                    # Runtime volume mount (finally.db, gitignored)
├── Dockerfile             # Multi-stage: Node → Python
├── docker-compose.yml     # Optional convenience
└── .env                   # Gitignored (.env.example committed)
```

**Boundaries:** `frontend/` and `backend/` are self-contained. Frontend talks to backend via `/api/*`. Backend owns DB init, schema, seeds, routes, SSE, market data, and LLM. Neither modifies the other's code. API contract (Section 7) is the shared interface.

## 5. Environment Variables

```bash
OPENROUTER_API_KEY=...       # Required: LLM chat
MASSIVE_API_KEY=             # Optional: Polygon.io real data (simulator if absent)
LLM_MOCK=false               # Optional: deterministic mock responses for testing
```

## 6. Market Data

Both simulator and Massive client implement the same abstract interface. Selection is automatic based on `MASSIVE_API_KEY`.

**Simulator (default):** GBM with per-ticker drift/volatility, ~500ms updates, correlated moves, random 2-5% events, realistic seed prices. New unknown tickers get default GBM params (drift=0, vol=0.02, price=$100).

**Massive/Polygon.io (optional):** REST polling. Free tier: 15s interval. Paid: 2-15s.

**Shared price cache:** In-memory, holds latest/previous price + timestamp per ticker. SSE reads from cache.

**SSE streaming** (`GET /api/stream/prices`): Long-lived connection, pushes watchlist ticker updates ~500ms, heartbeat every 15-30s (`: ping\n\n`). Client uses native `EventSource` with auto-reconnect. No reconnection needed on watchlist change.

## 7. Database

SQLite with lazy initialization — creates schema and seeds on first request if missing.

All tables have `user_id TEXT DEFAULT "default"` for future multi-user. Use Python `Decimal` for financial math; store cash/prices at 2 decimal places; GBM floats rounded at DB boundaries.

**Tables:**

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `users_profile` | id, cash_balance (default 10000), created_at | Single row for v1 |
| `watchlist` | id, user_id, ticker, added_at | UNIQUE(user_id, ticker) |
| `positions` | id, user_id, ticker, quantity, avg_cost, updated_at | UNIQUE(user_id, ticker) |
| `trades` | id, user_id, ticker, side, quantity, price, executed_at | Append-only log |
| `portfolio_snapshots` | id, user_id, total_value, recorded_at | Every 30s + after trades |
| `chat_messages` | id, user_id, role, content, actions (JSON), created_at | Full history kept |

**Constraints:** `cash_balance >= 0`, `quantity > 0`, `side IN ('buy','sell')`

**Indexes:** `watchlist(user_id,ticker)`, `positions(user_id)`, `trades(user_id,executed_at)`, `portfolio_snapshots(user_id,recorded_at)`

**Retention:** Snapshots capped at 7-30 days full resolution, sample to 1/day after. Cap ~50k rows/user.

**Seed data:** Default user with $10k, watchlist [AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX], initial portfolio snapshot at $10k.

## 8. API Endpoints

### Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE price stream |
| GET | `/api/portfolio` | Positions, cash, total value, P&L |
| POST | `/api/portfolio/trade` | Execute trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio snapshots for P&L chart |
| GET | `/api/watchlist` | Watchlist with latest prices |
| POST | `/api/watchlist` | Add ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove ticker |
| POST | `/api/chat` | Chat message → response + actions |
| GET | `/api/health` | Health check |

### Error Format

```json
{"error": "message", "code": "ERROR_CODE"}
```

Codes: `INVALID_TICKER` (400), `TICKER_NOT_FOUND` (404), `INSUFFICIENT_CASH` (400), `INSUFFICIENT_SHARES` (400), `INVALID_QUANTITY` (400), `INVALID_SIDE` (400), `LLM_ERROR` (500), `INTERNAL_ERROR` (500)

### Response Examples

**GET /api/portfolio:**
```json
{
  "cash_balance": 8500.50,
  "total_value": 12350.75,
  "positions": [{
    "ticker": "AAPL", "quantity": 10.0, "avg_cost": 185.50,
    "current_price": 190.25, "market_value": 1902.50,
    "unrealized_pnl": 47.50, "unrealized_pnl_pct": 2.56
  }]
}
```

**POST /api/portfolio/trade:** Request `{ticker, quantity, side}` → Response `{success, trade: {id, ticker, side, quantity, price, executed_at}, new_cash_balance, new_position}`

**GET /api/portfolio/history:** `{snapshots: [{total_value, recorded_at}, ...]}`

**GET /api/watchlist:** `{tickers: [{ticker, current_price, previous_price, change_pct, added_at}, ...]}`

**POST /api/watchlist:** Request `{ticker}` → Response `{success, ticker, added_at}`

**POST /api/chat:** Request `{message}` → Response `{message, trades: [{ticker, side, quantity, price, success}], watchlist_changes: [], errors: []}`

**GET /api/health:** `{status: "healthy", database: "connected", market_data: "running"}`

### Validation Rules

- **Tickers:** 1-5 chars, `[A-Z0-9.-]`, auto-uppercased. Simulator registers unknown tickers with defaults.
- **Trades:** Min quantity 1 share. Cash validated for buys, shares validated for sells. Concurrent trades serialized via `asyncio.Lock` or `BEGIN IMMEDIATE`.

## 9. LLM Integration

Uses LiteLLM via OpenRouter with `openrouter/openai/gpt-oss-120b` model (Cerebras inference). Uses structured outputs.

**Flow:** User message → load portfolio context + last 15-25 messages (capped ~4000 tokens) → LLM call → parse structured JSON → auto-execute trades/watchlist changes (best-effort, continues on failure) → store in `chat_messages` → return response.

**Structured output schema:**
```json
{
  "message": "response text",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add|remove"}]
}
```

Trades auto-execute without confirmation (simulated money, zero stakes). Failed trades included as errors in response. LLM prompted as "FinAlly, an AI trading assistant" — concise, data-driven, structured JSON.

**Mock mode** (`LLM_MOCK=true`): Deterministic responses for E2E tests and dev without API key.

## 10. Frontend

Single-page app, terminal-inspired layout. Tailwind CSS dark theme.

**UI elements:** Watchlist panel (prices, sparklines, change %), main chart area (selected ticker), portfolio heatmap (treemap), P&L line chart, positions table, trade bar (ticker/quantity/buy/sell), AI chat sidebar (collapsible), header (total value, cash, connection status).

**Tech:** `EventSource` for SSE, canvas charting (Lightweight Charts or Recharts), React Context for state (prices, portfolio, watchlist, chat contexts). Prices: SSE-authoritative. Portfolio/watchlist: API-authoritative after mutations (refetch on trade/watchlist change).

## 11. Docker & Deployment

**Multi-stage build:** Stage 1 (Node 20) builds frontend static export. Stage 2 (Python 3.12) installs uv + backend deps, copies static output, serves everything on port 8000.

**Volume:** `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`

**Scripts:** `scripts/start_mac.sh`, `stop_mac.sh`, `start_windows.ps1`, `stop_windows.ps1` — all idempotent.

## 12. Background Tasks & Observability

**Tasks:** Market data (~500ms), portfolio snapshots (30s), snapshot cleanup (daily). Start on FastAPI startup, stop on shutdown via lifespan events. Use `asyncio.create_task()`.

**Logging:** Python `logging`, structured JSON, stdout/stderr. Request IDs for tracing. Log SSE connections and all trades with full context.

**Health:** `/api/health` reports DB, market data task, and snapshot task status.

## 13. Performance Targets

| Metric | Target |
|--------|--------|
| SSE latency | <100ms |
| API response (non-chat) | p95 <200ms |
| Chat response | p95 <2s |
| Trade execution | <50ms |
| Frontend animations | 60fps |
| DB queries | <10ms |
| Concurrent SSE | 100+ connections |

## 14. Known Limitations (v1)

Single-user only, market orders only, no historical prices (sparklines reset on reload), no after-hours/corporate actions/fees/slippage/portfolio analytics/news feed.

## 15. Development Workflow

1. **Backend first** — DB, API, market data functional before frontend integrates
2. **Parallel dev** — once API contracts defined, frontend/backend work simultaneously
3. **Integration** — test SSE, API responses, error handling at boundaries
4. **E2E tests last** — after both sides functional

Frontend does NOT modify backend code. Backend does NOT modify frontend code. API contract changes go through Section 8 first.

## 16. Testing Strategy

**Backend (pytest):** Market data (GBM, interface conformance), portfolio (trade logic, P&L, edge cases), LLM (structured output parsing, malformed handling), API routes (status codes, response shapes).

**Frontend (React Testing Library):** Component rendering, price flash triggers, watchlist CRUD, portfolio display, chat rendering.

**E2E (Playwright in `test/`):** Via `docker-compose.test.yml` with `LLM_MOCK=true`. Scenarios: fresh start, watchlist CRUD, buy/sell, portfolio viz, AI chat, SSE reconnection.
