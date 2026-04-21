# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist. Frontend builds sparklines entirely from SSE price events received since page load (no historical data backend). Sparklines start empty and fill in progressively as prices arrive.
- **Click a ticker** to see a larger detailed chart in the main chart area (also built from SSE data since page load)
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision                | Rationale                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------- |
| SSE over WebSockets     | One-way push is all we need; simpler, no bidirectional complexity, universal browser support  |
| Static Next.js export   | Single origin, no CORS issues, one port, one container, simple deployment                     |
| SQLite over Postgres    | No auth = no multi-user = no need for a database server; self-contained, zero config          |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration          |
| uv for Python           | Fast, modern Python project management; reproducible lockfile; what students should learn     |
| Market orders only      | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
# Note: Massive is Polygon.io's market data service
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Polygon.io REST API for real market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

**Note:** "Massive" refers to Polygon.io's market data service. The environment variable name `MASSIVE_API_KEY` is used throughout the codebase for consistency.

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies
- **New ticker handling:** When a ticker not in the seed list is added to watchlist, register it with default GBM parameters (drift=0.0, volatility=0.02, starting price=$100.00). This provides a simpler UX than rejecting unknown tickers.

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for the default user's watchlist tickers at a regular cadence (~500ms)
- When the watchlist changes, the next SSE events naturally reflect the new set (no reconnection needed)
- Optional heartbeat: send a comment line (`: ping\n\n`) every 15-30 seconds to keep proxies happy
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**Decimal Precision:**
- Use Python `Decimal` type for all financial calculations (cash, position values, P&L)
- Store cash and prices with 2 decimal places (cents for USD)
- Quantities: fractional shares stored with 2-6 decimal places
- GBM simulator can use floats but must round at boundaries when writing to database

**users_profile** — User state (cash balance)

- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution.

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**Retention Policy:** Keep last 7-30 days at full 30-second resolution. Delete older snapshots or sample to 1/day to prevent unbounded growth. Cap at ~50k rows per user.

**Indexes:**
- `watchlist(user_id, ticker)`
- `positions(user_id)`
- `trades(user_id, executed_at)`
- `portfolio_snapshots(user_id, recorded_at)`

**CHECK Constraints:**
- `cash_balance >= 0`
- `quantity > 0`
- `side IN ('buy', 'sell')`

**chat_messages** — Conversation history with LLM

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX
- Initial portfolio snapshot: `total_value=10000.0`, `recorded_at=<creation timestamp>` (so P&L chart isn't empty on first launch)

---

## 8. API Endpoints

### Market Data

| Method | Path                 | Description                      |
| ------ | -------------------- | -------------------------------- |
| GET    | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio

| Method | Path                     | Description                                                  |
| ------ | ------------------------ | ------------------------------------------------------------ |
| GET    | `/api/portfolio`         | Current positions, cash balance, total value, unrealized P&L |
| POST   | `/api/portfolio/trade`   | Execute a trade: `{ticker, quantity, side}`                  |
| GET    | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart)          |

### Watchlist

| Method | Path                      | Description                                  |
| ------ | ------------------------- | -------------------------------------------- |
| GET    | `/api/watchlist`          | Current watchlist tickers with latest prices |
| POST   | `/api/watchlist`          | Add a ticker: `{ticker}`                     |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker                              |

### Chat

| Method | Path        | Description                                                                 |
| ------ | ----------- | --------------------------------------------------------------------------- |
| POST   | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System

| Method | Path          | Description                          |
| ------ | ------------- | ------------------------------------ |
| GET    | `/api/health` | Health check (for Docker/deployment) |

### API Response Schemas

**Standard Error Response:**
```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE"
}
```

Common error codes:
- `INVALID_TICKER` - Ticker format invalid (400)
- `TICKER_NOT_FOUND` - Ticker not in watchlist (404)
- `INSUFFICIENT_CASH` - Not enough cash for buy (400)
- `INSUFFICIENT_SHARES` - Not enough shares for sell (400)
- `INVALID_QUANTITY` - Quantity out of valid range (400)
- `INVALID_SIDE` - Side must be 'buy' or 'sell' (400)
- `LLM_ERROR` - LLM API call failed (500)
- `INTERNAL_ERROR` - Unexpected server error (500)

**GET /api/portfolio:**
```json
{
  "cash_balance": 8500.50,
  "total_value": 12350.75,
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10.0,
      "avg_cost": 185.50,
      "current_price": 190.25,
      "market_value": 1902.50,
      "unrealized_pnl": 47.50,
      "unrealized_pnl_pct": 2.56
    }
  ]
}
```

**POST /api/portfolio/trade** (Request):
```json
{
  "ticker": "AAPL",
  "quantity": 10,
  "side": "buy"
}
```

**POST /api/portfolio/trade** (Response):
```json
{
  "success": true,
  "trade": {
    "id": "uuid-here",
    "ticker": "AAPL",
    "side": "buy",
    "quantity": 10.0,
    "price": 190.25,
    "executed_at": "2024-01-15T10:30:00Z"
  },
  "new_cash_balance": 6597.00,
  "new_position": {
    "ticker": "AAPL",
    "quantity": 10.0,
    "avg_cost": 190.25
  }
}
```

**GET /api/portfolio/history:**
```json
{
  "snapshots": [
    {
      "total_value": 10000.00,
      "recorded_at": "2024-01-15T10:00:00Z"
    },
    {
      "total_value": 10125.50,
      "recorded_at": "2024-01-15T10:00:30Z"
    }
  ]
}
```

**GET /api/watchlist:**
```json
{
  "tickers": [
    {
      "ticker": "AAPL",
      "current_price": 190.25,
      "previous_price": 189.50,
      "change_pct": 0.40,
      "added_at": "2024-01-15T09:00:00Z"
    }
  ]
}
```

**POST /api/watchlist** (Request):
```json
{
  "ticker": "PYPL"
}
```

**POST /api/watchlist** (Response):
```json
{
  "success": true,
  "ticker": "PYPL",
  "added_at": "2024-01-15T10:30:00Z"
}
```

**POST /api/chat** (Request):
```json
{
  "message": "Buy 5 shares of AAPL"
}
```

**POST /api/chat** (Response):
```json
{
  "message": "I've purchased 5 shares of AAPL at $190.25. Your new cash balance is $9048.75.",
  "trades": [
    {
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 5,
      "price": 190.25,
      "success": true
    }
  ],
  "watchlist_changes": [],
  "errors": []
}
```

**GET /api/health:**
```json
{
  "status": "healthy",
  "database": "connected",
  "market_data": "running"
}
```

**Ticker Validation:**
- Format: 1-5 characters, `[A-Z0-9.-]`, automatically uppercased
- Semantic validation: If Massive API enabled, validate via API; if simulator, accept only known tickers or register new ones with default GBM parameters (to be decided)
- Invalid tickers return 400 with `INVALID_TICKER` error code

**Trade Validation:**
- Minimum quantity: 1 share (or 0.01 if fractional shares enabled)
- Maximum quantity: No hard limit, but validated against available cash (buys) or shares (sells)
- Cash validation: `cash_balance >= quantity * current_price` for buys
- Shares validation: `position.quantity >= quantity` for sells
- Concurrent trades: Serialized per user using asyncio.Lock or BEGIN IMMEDIATE transaction

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table (last 15-25 messages, capped at ~4000 tokens total for history)
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response (best-effort: executes in array order, continues on failure, returns per-trade errors)
7. Stores the message and executed actions (including any errors) in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

**Chat Message History Management:**
- Include last 15-25 messages in LLM context
- Cap total history at ~4000 tokens (truncate oldest messages if exceeded)
- Keep all messages in database indefinitely for v1 (single user, SQLite handles this easily)
- If a message would cause token overflow, drop oldest messages until under budget

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [{ "ticker": "AAPL", "side": "buy", "quantity": 10 }],
  "watchlist_changes": [{ "ticker": "PYPL", "action": "add" }]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells). Executed in array order, best-effort (continues on failure).
- `watchlist_changes` (optional): Array of watchlist modifications. Each object has `ticker` (string) and `action` ("add" | "remove")

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:

- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:

- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:

- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

**State Management:**
- Use React Context for global state (simple app, no need for Zustand/Redux)
- Separate contexts for: prices (from SSE), portfolio (from API), watchlist (from API), chat

**State Reconciliation:**
- Prices: SSE is authoritative; update local state on each SSE event
- Portfolio/Watchlist: API is authoritative after mutations
- After successful trade POST: refetch portfolio via GET (or optimistic update then confirm)
- After watchlist add/remove: refetch watchlist (SSE will naturally include/exclude ticker in next events)

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):

- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):

- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Performance Targets

- **SSE latency:** <100ms from price update to client receive
- **API response time:** p95 <200ms for all endpoints except chat
- **Chat response time:** p95 <2s (depends on LLM API)
- **Trade execution:** <50ms from request to database commit
- **Frontend render:** 60fps for price flash animations
- **Database queries:** <10ms for all standard queries
- **Concurrent SSE connections:** Support at least 100 concurrent connections (future-proofing)

---

## 13. Known Limitations

These are deliberate simplifications for v1:

- **Single-user only** - No authentication, everyone uses "default" user
- **Market orders only** - No limit orders, stop loss, or other order types
- **No historical price data** - Sparklines reset on page reload (built from SSE since load)
- **No after-hours trading** - Simulator runs continuously, but real markets have hours
- **No corporate actions** - No dividends, splits, mergers, etc.
- **No transaction fees** - All trades execute at exact market price with zero commission
- **No slippage** - Instant fills at current price (unrealistic for large orders)
- **No portfolio analytics** - No Sharpe ratio, beta, alpha, etc.
- **No news feed** - No integration with financial news APIs

---

## 14. Development Workflow

**Agent Coordination:**

1. **Backend First** - Database schema, API contracts, market data simulator must be functional before frontend can integrate
2. **Parallel Development** - Once API contracts defined, frontend and backend agents can work simultaneously
3. **Integration Points** - Test SSE streaming, API responses, and error handling at boundaries
4. **Testing Last** - E2E tests written after both frontend and backend are functional

**Handoff Process:**

- Backend agent delivers: working API endpoints, documented in section 8, runnable via `uvicorn`
- Frontend agent delivers: static build in `frontend/out/`, documented in README
- Integration agent: combines in Dockerfile, tests end-to-end
- Testing agent: writes comprehensive E2E test suite

**Handling Integration Issues:**

- Frontend agent should NOT modify backend code (use API as contract)
- Backend agent should NOT modify frontend code (serve static files only)
- If API contract needs changes: update section 8 first, then both agents adapt
- Use `planning/` directory for inter-agent communication and spec clarifications

---

## 15. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:

- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:

- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:

- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 16. Background Tasks & Observability

**Background Tasks:**

1. **Market Data Task** - Updates price cache every ~500ms (simulator) or polls Massive API at configured interval
2. **Portfolio Snapshot Task** - Records total portfolio value every 30 seconds
3. **Snapshot Cleanup Task** - Runs daily to prune snapshots older than retention period

**Lifecycle Management:**
- Tasks start on FastAPI startup via `@app.on_event("startup")`
- Tasks stop gracefully on shutdown via `@app.on_event("shutdown")`
- Use `asyncio.create_task()` for background tasks
- Tasks should handle exceptions and log errors without crashing

**Logging Strategy:**
- Use Python `logging` module with structured JSON format
- Log levels: DEBUG (development), INFO (production), WARNING (issues), ERROR (failures)
- Log to stdout/stderr (Docker captures these)
- Include request IDs in all API logs for tracing
- Log all SSE connections (connect/disconnect events)
- Log all trades with full context (user, ticker, quantity, price, timestamp, success/failure)

**Health Checks:**
- `/api/health` returns 200 once database is initialized
- Include status of: database connection, market data task, snapshot task
- Use for Docker HEALTHCHECK and orchestration readiness probes

---

## 17. Document Review & Questions

### Critical Questions Requiring Clarification

1. **Chat Message History Management**
   - Q: How many messages should be included in the LLM context window?
   - A: Cap by both message count and approximate tokens. E.g. last 15–25 messages, but if the total exceeds a token budget, truncate from the oldest until under budget.

   - Q: Should there be a token limit calculation, or just a fixed message count (e.g., last 20 messages)?
   - A: Hybrid: fixed count is simple to implement; token budget (e.g. 3k–6k tokens for history + prompt + system, depending on model window) avoids surprise overflows when messages are long.

   - Q: Should very old messages be pruned from the database, or keep indefinitely?
   - A: Keep messages indefinitely for v1 (single user, SQLite). Add optional pruning later (e.g. delete older than 90 days) if DB size matters.

2. **Ticker Validation**
   - Q: What happens if a user (or AI) tries to add an invalid ticker symbol to the watchlist?
   - A: Reject with 400 and a clear error: {"error": "...", "code": "INVALID_TICKER"}. Don’t add to DB.

   - Q: Should the backend validate tickers against a known list, or accept any string?
   - A: Format validation always (e.g. 1–5 chars, [A-Z0-9.-], uppercase). Semantic validation: if Massive is on, check via API (or a lightweight “snapshot” quote); if simulator-only, allow only tickers the sim knows or register new tickers into the sim with a default price/volatility.

   - Q: How should the simulator handle newly added tickers it hasn't seen before?
   - A: Define behavior: either “unknown ticker → error until seed list extended” or “add with default GBM params” (simpler UX).

3. **Portfolio Snapshots Growth**
   - Q: With snapshots every 30 seconds, the table grows unbounded. Should there be a retention policy (e.g., keep last 7 days)?
   - A: Yes: e.g. 7–30 days at 30s resolution, then optional roll-up to hourly for longer (or cap total rows per user, e.g. 50k).

   - Q: Should older snapshots be aggregated to hourly/daily granularity for long-term history?
   - A: Nice-to-have v2. For v1: delete or sample old points (e.g. keep 1/day after N days) to stop growth.

4. **Trade Concurrency**
   - Q: What happens if a user submits multiple trades simultaneously (e.g., clicking buy rapidly)?
   - A: Serialize trades per user (single SQLite writer pattern): one queue or asyncio.Lock around trade handler, or DB transaction that validates cash/shares atomically.

   - Q: Should there be database-level locking or optimistic concurrency control?
   - A: SQLite + short transactions is usually enough: BEGIN IMMEDIATE (or equivalent serialized access) for the trade path. Optimistic is overkill here.

   - Q: Can the AI execute multiple trades in a single chat response, and how are they ordered?
   - A: Execute in array order (as returned). Stop or continue on first failure — pick one and document: e.g. all-or-nothing in a single transaction, or best-effort with per-trade errors returned in the chat payload.

5. **SSE Connection Lifecycle**
   - Q: Should there be a heartbeat/ping mechanism to detect stale connections?
   - A: Optional comment/ping event every 15–30s helps proxies; many apps rely on periodic price events as implicit heartbeat. Add explicit : ping\n\n or event: ping if you see timeouts.

   - Q: What happens to the SSE stream when the user's watchlist changes?
   - A: No need to reconnect. Server streams union of watchlist tickers (or “all symbols in cache”); when watchlist updates, next SSE events naturally reflect new set.

   - Q: Should the server track active SSE connections per user for future multi-user support?
   - A: v1: optional counter only. For future multi-user, you’ll need connection ↔ user mapping; not required for "default" now.

6. **Decimal Precision**
   - Q: What decimal precision should be used for prices, quantities, and cash balances?
   - A: USD: 2 decimal places for display and stored cash; prices often ≥ 2 (2–4 depending on asset — 2 is fine for this demo). Quantities: integers only if you adopt simplification #1; else 2–6 decimal places for fractional shares.

   - Q: Should calculations use Decimal type in Python to avoid floating-point errors?
   - A : Yes for money paths (cash, position value, P&L); floats OK for ephemeral GBM if you round at boundaries.

   - Q: How should rounding work (e.g., round to nearest cent for USD)?
   - A: Round half away from zero or banker’s — pick one; consistency matters more than which for a simulator.

7. **Frontend State Management**
   - Q: Should the frontend use a state management library (Zustand, Redux) or React context?
   - A: React context is fine for this simple app.
   - Q: How should the frontend reconcile SSE price updates with API responses (e.g., after a trade)?
   - A: After trade POST succeeds, refetch portfolio (or apply optimistic update then confirm). Prices stay SSE-authoritative; positions/cash are API-authoritative after mutations

8. **Error Recovery**
   - Q: If a trade execution fails mid-chat-response, should the LLM message still be saved?
   - A: Yes: save assistant message with actions noting failures (and errors inline in structured JSON), so the UI stays honest.

   - Q: Should failed trades be logged to a separate table for debugging?
   - A: Optional. For v1: actions JSON + app logs is enough. Add trade_failures table only if debugging needs it.

### Missing Specifications

1. **API Response Schemas**
   - All endpoints should specify exact response shapes with example JSON
   - Error response format not defined (status codes mentioned but not response bodies)
   - Pagination strategy for `/api/portfolio/history` not specified (could be thousands of snapshots)

2. **Watchlist Changes Schema**
   - The LLM structured output shows `"action": "add"` but doesn't specify `"remove"` action
   - Should be: `{"ticker": "PYPL", "action": "add" | "remove"}`

3. **Trade Validation Rules**
   - Minimum trade quantity not specified (can user buy 0.00001 shares?)
   - Maximum trade size not specified (can user buy a billion shares if they have cash?)
   - Should there be a max position size per ticker (e.g., 100% portfolio in one stock)?

4. **Background Task Lifecycle**
   - When do background tasks (market data, portfolio snapshots) start?
   - How are they gracefully shut down on container stop?
   - Should they use structured logging for observability?

5. **Logging & Observability**
   - No logging strategy specified (stdout/stderr? structured JSON logs?)
   - Should there be request ID tracking for debugging?
   - Should SSE connections be logged with connect/disconnect events?

6. **Rate Limiting**
   - Should API endpoints have rate limiting to prevent abuse?
   - Should the chat endpoint have a rate limit to manage API costs?

7. **Startup Sequence**
   - Should the backend health check endpoint return unhealthy until database is initialized?
   - Should there be a startup probe vs liveness probe distinction?

### Opportunities for Improvement

1. **Schema Enhancements**
   - Add indexes: `watchlist(user_id, ticker)`, `positions(user_id)`, `trades(user_id, executed_at)`, `portfolio_snapshots(user_id, recorded_at)`
   - Add `CHECK` constraints: `cash_balance >= 0`, `quantity > 0`, `side IN ('buy', 'sell')`
   - Add `ON DELETE CASCADE` for user_id foreign keys (future multi-user)

2. **API Improvements**
   - Add `GET /api/trades` endpoint to retrieve trade history (currently write-only)
   - Add `GET /api/chat/history` to retrieve chat without sending a new message
   - Add request/response examples to section 8 for each endpoint

3. **Error Handling Patterns**
   - Define standard error response format: `{"error": "message", "code": "INSUFFICIENT_CASH"}`
   - Specify HTTP status codes for each error type (400 vs 422 vs 500)
   - Add error handling guidance for LLM integration (malformed JSON, missing API key, timeout)

4. **Observability**
   - Add structured logging with log levels (DEBUG, INFO, WARNING, ERROR)
   - Add request ID middleware for tracing API calls
   - Add metrics endpoint (`/api/metrics`) for monitoring (optional)
   - Log all trades with full context (user, ticker, quantity, price, timestamp, success/failure)

5. **Testing Additions**
   - Add load testing guidance (how many concurrent SSE connections can the backend handle?)
   - Add mutation testing for critical portfolio math
   - Specify test coverage targets (80% minimum per global rules)

6. **Security Considerations**
   - Add input sanitization guidance for ticker symbols (alphanumeric only, max length)
   - Add CORS configuration guidance (even though same-origin, good to be explicit)
   - Add Content-Security-Policy headers for production
   - Validate that OPENROUTER_API_KEY is set on startup (fail fast if missing)

7. **Documentation**
   - Add API documentation generation (OpenAPI/Swagger) as optional enhancement
   - Add architecture diagram (could be generated with Mermaid in markdown)
   - Add sequence diagrams for key flows (trade execution, chat with auto-execute)

### Opportunities for Simplification

1. **Remove Fractional Shares (v1)**
   - Fractional shares add complexity: validation, display formatting, edge cases
   - Simplify to integer quantities only for initial version
   - Can add fractional shares in v2 if needed
   - Changes: `quantity` REAL → INTEGER, validation logic simpler

2. **Reduce Default Watchlist**
   - 10 tickers might be overwhelming on first launch
   - Consider 5 tickers: AAPL, MSFT, GOOGL, TSLA, NVDA (top tech)
   - Faster initial render, less data to stream

3. **Simplify Portfolio Snapshots**
   - Instead of every 30 seconds + after each trade, just do after each trade
   - For continuous chart, frontend can interpolate between snapshots
   - Reduces database writes by ~95% for typical usage
   - Simpler background task logic

4. **Merge User Profile Into Config**
   - `users_profile` table with one row feels over-engineered for single-user
   - Could store cash balance in a simple JSON config file or environment variable
   - Reduces database complexity, one fewer table to manage

5. **Simplify Directory Structure Documentation**
   - Section 4 has redundant explanations between the tree and "Key Boundaries"
   - Could consolidate into just the tree with inline comments
   - Reduce cognitive load for developers

6. **Simplify SSE Streaming**
   - "All tickers known to the system" is ambiguous
   - Clarify: stream only the default user's watchlist
   - Remove mention of "future multi-user" to reduce complexity

7. **Remove "Optional Cloud Deployment" Section**
   - Terraform/App Runner is marked as "stretch goal, not part of core build"
   - Including it in the plan adds cognitive overhead
   - Move to a separate DEPLOYMENT.md if implemented

### Suggested Additions

1. **Add Section: Performance Targets**
   - SSE latency: <100ms from price update to client receive
   - API response time: p95 <200ms for all endpoints
   - Trade execution: <50ms from request to database commit
   - Frontend render: 60fps for price flash animations

2. **Add Section: Development Workflow**
   - How should agents coordinate? (e.g., backend first, then frontend)
   - What is the handoff process between agents?
   - How to handle integration issues between frontend/backend?

3. **Add Section: Known Limitations**
   - Single-user only (no authentication)
   - Market orders only (no limit orders, stop loss, etc.)
   - No historical data persistence (sparklines reset on page reload)
   - No dark pool, no after-hours trading simulation
   - No dividends, splits, or corporate actions

4. **Add Section: Future Enhancements**
   - Multi-user support with authentication
   - Historical price data storage
   - Limit orders and order book
   - Real-time news integration
   - Portfolio analytics (Sharpe ratio, beta, etc.)
   - Export trade history to CSV

### Consistency Issues

1. **Sparkline Data Source**
   - Section 2 says "accumulated on the frontend from SSE since page load"
   - But no backend endpoint provides historical data for sparklines
   - Should clarify: frontend builds sparklines entirely from SSE events it receives (no historical data)

2. **Portfolio P&L Chart**
   - Section 2 mentions "P&L chart tracking total portfolio value over time"
   - Section 7 says snapshots recorded "every 30 seconds"
   - But new users will have no historical data on first launch
   - Should seed initial snapshot on user creation, or clarify chart will be empty initially

3. **Massive API Naming**
   - Document refers to both "Massive API" and "Polygon.io"
   - Should clarify relationship: Massive is built on Polygon.io, or they're the same
   - Environment variable is `MASSIVE_API_KEY` but might need to clarify which service

4. **LLM Model Reference**
   - Section 9 says "use cerebras-inference skill"
   - But the specific model is `openrouter/openai/gpt-oss-120b`
   - Should verify this model is current and available
   - Should specify fallback model if primary is unavailable

### High-Priority Recommendations

1. **Define API Response Format Standard** (HIGH)
   - Add section 8.1 with example responses for every endpoint
   - Include error response format
   - This unblocks frontend/backend integration

2. **Specify Decimal Precision** (HIGH)
   - Financial calculations require precision
   - Recommend: Python Decimal type, 2 decimal places for USD, 6 for quantity
   - Add to section 7 schema notes

3. **Add Ticker Validation** (MEDIUM)
   - Prevents user/AI from adding invalid symbols
   - Recommend: alphanumeric only, 1-5 characters, uppercase
   - Add new API endpoint: `GET /api/tickers/validate/{ticker}`

4. **Add Snapshot Retention Policy** (MEDIUM)
   - Prevent unbounded database growth
   - Recommend: keep last 7 days at full resolution, then aggregate to hourly
   - Add to section 7 under portfolio_snapshots

5. **Clarify Chat Message Limit** (MEDIUM)
   - Prevents token overflow
   - Recommend: last 20 messages or 4000 tokens, whichever is smaller
   - Add to section 9 under "How It Works"

6. **Remove Fractional Shares for v1** (LOW - Simplification)
   - Reduces complexity significantly
   - Integer-only shares are more intuitive for demo
   - Can add in v2 if needed
