# MiniTrade — Trading & Portfolio Tracker

A small full-stack app for **virtual** trading: browse stocks, keep a watchlist, place market
BUY/SELL orders and track portfolio P&L. All prices are **synthetic sample data** — no real market
data and no real money is involved.

| Layer    | Tech                                                    |
|----------|---------------------------------------------------------|
| Database | PostgreSQL 13+ (plain SQL, no ORM)                      |
| Backend  | Python 3.11+, Flask, psycopg2 — `routes → services → repositories` |
| Frontend | React 18, React Router 6, Vite (functional components + hooks, Context for shared state) |

```
minitrade/
├── db/
│   ├── schema.sql         tables, keys, constraints, indexes
│   ├── seed.sql           5 users, 14 stocks, 30 trading days of OHLC each, watchlists
│   ├── seed_orders.sql    optional demo trade history (so Portfolio / Q2 / Q3 show data)
│   ├── queries.sql        Part A: Q1–Q5
│   └── explain_demo.sql   EXPLAIN before/after an index (rolls back, safe to run)
├── backend/               Flask API  (app/routes, app/services, app/repositories, tests/)
├── frontend/              React app  (src/pages, components, context, hooks, api)
└── README.md
```

---

## 1. Run it

You need **PostgreSQL**, **Python 3.11+** and **Node 18+**.

### 1.1 Database
```bash
createdb minitrade                       # or create it with pgAdmin / any client
# Option A – with psql
psql minitrade -f db/schema.sql
psql minitrade -f db/seed.sql
psql minitrade -f db/seed_orders.sql     # optional demo trades (skip for a clean ₹1,00,000 start)

# Option B – without psql (uses the Python driver; see 1.2 first)
cd backend && python scripts/init_db.py          # schema + seed + demo trades
cd backend && python scripts/init_db.py --clean  # schema + seed only
```

### 1.2 Backend (http://localhost:8000)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit DATABASE_URL (user / password / db name)
python run.py
curl http://localhost:8000/api/health      # -> {"data":{"status":"ok"}}
```

### 1.3 Frontend (http://localhost:5173)
```bash
cd frontend
npm install
cp .env.example .env            # only needed if the API is not on http://localhost:8000/api
npm run dev
```

### 1.4 Backend tests (real PostgreSQL, no mocks for the data layer)
```bash
createdb minitrade_test
cd backend
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/minitrade_test
python -m unittest discover -s tests -v      # 39 tests
```
> ⚠️ The tests run `schema.sql` on `TEST_DATABASE_URL` (drops and recreates all tables). Use a throw-away database.

### Configuration (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/minitrade` | PostgreSQL connection string |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | origins allowed to call the API (`*` = any) |
| `DEMO_USER_ID` | `1` | the user the API acts as (there is no login) |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | pagination limits |
| `PORT` | `8000` | backend port |
| `VITE_API_BASE_URL` (frontend) | `http://localhost:8000/api` | where the frontend finds the API |

---

## 2. Business rules and where they are enforced

| Rule | Enforced in |
|---|---|
| Demo user starts with ₹1,00,000 | `users.wallet_balance DEFAULT 100000.00` + `seed.sql` |
| 10+ stocks × 30 days OHLC | `seed.sql` → 14 stocks × 30 weekdays |
| Market orders only, executed at the latest close | `order_service.place_order` reads the latest `price_history` row; there is no price field in the request |
| BUY needs balance, SELL needs holdings, else reject with a clear error | `order_service` → **422** `INSUFFICIENT_FUNDS` / `INSUFFICIENT_HOLDINGS`; additionally `CHECK (wallet_balance >= 0)` in the DB as a safety net |
| Order + wallet + holding change in **one** DB transaction | `db.transaction()` context manager: commit on success, rollback on any exception |
| Average buy price is a weighted average | `holdings_repo.add_shares` (see §4.2) |

---

## 3. REST API

Base URL `http://localhost:8000/api`. Every success body is `{"data": ...}` (lists also have `"pagination"`).
Every error has **one** shape:

```json
{ "error": { "code": "INSUFFICIENT_FUNDS", "message": "Insufficient wallet balance: ...", "details": { "required": 3363680.0, "available": 83181.6 } } }
```

| Method | Endpoint | Purpose | Status codes |
|---|---|---|---|
| GET | `/stocks` | Latest price + day change. Query: `search`, `sector`, `sort` (`symbol`, `name`, `price`, `change_pct`), `order` (`asc`/`desc`), `page`, `page_size` | 200, 400 |
| GET | `/stocks/{symbol}` | Details + 30-day OHLC history | 200, **404** unknown symbol |
| GET | `/watchlist` | The user's watchlist with latest prices | 200 |
| POST | `/watchlist` `{"symbol": "TCS"}` | Add a stock | 201, 400, **409** duplicate, 404 unknown symbol |
| DELETE | `/watchlist/{symbol}` | Remove a stock | 204, 404 if not in the watchlist |
| POST | `/orders` `{"symbol","side","quantity"}` | Place a market order | **201** ok, **400** invalid input, **422** rule failure, 404 unknown symbol |
| GET | `/orders` | History, newest first. Query: `symbol`, `side`, `page`, `page_size` | 200, 400 |
| GET | `/portfolio` | Wallet, holdings, invested vs current value, total P&L | 200 |
| GET | `/sectors`, `/health` | helper endpoints (sector filter list, liveness) | 200 |

Validation: body must be a JSON object; `symbol` a string; `side` `BUY`/`SELL` (case-insensitive);
`quantity` a **whole number** between 1 and 1,000,000 (booleans, floats and strings are rejected). All field errors
are reported together in `error.details.fields`. A well-formed order for a symbol that does not exist is a **404** (`STOCK_NOT_FOUND`);
**422** is reserved for trading-rule failures (not enough money / shares).

Quality attributes: parameterised queries everywhere (no string-built SQL values; the sort column comes from a whitelist),
CORS via env var, config via env vars, and a clean three-layer structure:

* `routes/` – HTTP only (parse request, call a service, shape the response)
* `services/` – business rules and transactions
* `repositories/` – SQL only; they receive a cursor, never a connection, so they cannot commit by accident

---

## 4. Design decisions

### 4.1 Schema (`db/schema.sql`)
* `users`, `stocks`, `price_history` (unique `(stock_id, trade_date)`), `watchlist` (composite PK), `orders`, `holdings`.
* **Money is `NUMERIC`**, never float: prices `NUMERIC(12,2)`, wallet `NUMERIC(14,2)`, average buy price `NUMERIC(14,4)`
  (extra decimals so repeated weighted averages do not drift). Python uses `Decimal`; money becomes a JSON number only at the API edge.
* Constraints do real work: `wallet_balance >= 0`, `quantity > 0`, `side IN ('BUY','SELL')`, OHLC sanity (`low <= open/close <= high`),
  foreign keys, and the watchlist composite PK (which is what makes the 409 reliable even under concurrency).
* `orders` is the **append-only source of truth**. `holdings` is a maintained summary (the brief allows it as optional) that
  makes the portfolio a cheap read; both are updated in the same transaction. A row is deleted when its quantity reaches 0.
* Indexes: `orders(user_id, created_at DESC)` for order history, `orders(created_at)` for Q3, `watchlist(stock_id)` for Q4,
  `price_history(trade_date)`, `stocks(sector)`.

### 4.2 Placing an order (the important function: `services/order_service.py`)
```
BEGIN
  read latest close for the symbol                      -- execution price
  SELECT ... FROM users WHERE id = ? FOR UPDATE         -- lock the user's row: one order at a time per user
  BUY : check wallet >= price*qty -> wallet -= cost -> upsert holding (weighted average)
  SELL: SELECT holding FOR UPDATE -> check owned >= qty -> wallet += proceeds -> reduce/delete holding
  INSERT order
COMMIT          (any exception, including a rule failure => ROLLBACK, nothing is half-applied)
```
The row lock means two simultaneous orders cannot both pass the balance check on the same money — there is a test for this.

Weighted average, done in SQL inside the upsert (right-hand sides see the *old* row):
`new_avg = (old_qty × old_avg + buy_qty × buy_price) / (old_qty + buy_qty)`. Selling does not change the average.

### 4.3 Frontend
* Screens: **Market** (search, sector filter, sort, pagination), **Stock detail** (30-day SVG chart, buy/sell form, watchlist button),
  **Portfolio**, **Orders** (filters + pagination), plus a **Watchlist** page.
* `TradingContext` holds the wallet/portfolio and the watchlist. After a trade the form calls `refreshPortfolio()` once and the header
  balance, the trade form's "You own" and the Portfolio page all update **without reloading**.
* Hooks: `useState`, `useEffect`, a custom `useApi` hook (loading / error / data / reload, cancels stale requests) and `useDebouncedValue` (search box).
* Every data screen handles **loading, error (with Retry) and empty** states. The chart is a small hand-written SVG component (no chart library).
* The UI only gives friendly hints; the **server is the authority** and its error message is shown if it rejects an order.

---

## 5. Written answers (Part A)

### INNER JOIN vs LEFT JOIN
`INNER JOIN` returns only rows that have a match on both sides. `LEFT JOIN` keeps **every** row of the left table and fills the
right side with `NULL` when there is no match. In this project:
* `holdings JOIN stocks` is an inner join — every holding has a stock, so nothing can be lost.
* **Q4b** "users who never placed an order" needs a `LEFT JOIN orders ... WHERE o.id IS NULL`: an inner join would drop exactly the users we are looking for.
* **Q3** uses `generate_series(...) LEFT JOIN orders` so a day with no trades shows `0` instead of disappearing from the report.

### Why order placement needs a transaction
One order changes three things: the **wallet**, the **holding** and the **orders** row. Without a transaction a crash or a failed check
between them would leave inconsistent money (wallet debited but no shares, shares but no order record, ...).
A transaction makes it **all-or-nothing** (atomicity). Combined with the `FOR UPDATE` row lock it also stops two concurrent orders from
both spending the same balance (isolation). Rule failures (422) are raised inside the transaction, so everything rolls back automatically.

### EXPLAIN before and after adding an index
Query: the Orders screen — newest 20 orders of one user — on 401,000 orders (`db/explain_demo.sql`, rolls back afterwards):
```sql
SELECT id, stock_id, side, quantity, price, created_at FROM orders WHERE user_id = 1 ORDER BY created_at DESC LIMIT 20;
```
**Before** (no index on `user_id`): reads the whole table, throws away ~400k rows, then sorts.
```
Limit (actual time=16.459..16.693 rows=20)
  -> Gather Merge
     -> Sort (Sort Key: created_at DESC, top-N heapsort)
        -> Parallel Seq Scan on orders (Filter: user_id = 1, Rows Removed by Filter: 133202)
Buffers: shared hit=3553      Execution Time: 16.715 ms
```
**After** `CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC)`: the index already holds that user's rows in the
requested order, so Postgres reads just the first 20 index entries — no scan, no sort.
```
Limit (actual time=0.029..0.048 rows=20)
  -> Index Scan using idx_orders_user_created on orders (Index Cond: user_id = 1)
Buffers: shared hit=20 read=3      Execution Time: 0.063 ms
```
≈ **260× faster**, and the cost stays flat as the table grows (the sequential scan grows with table size). Column order matters:
the equality column (`user_id`) first, the sort column (`created_at`) second.
(Timings are from my machine; yours will differ but the plan shape is the same.)

### Query notes
* **Q1** `LAG(close) OVER (PARTITION BY stock_id ORDER BY trade_date)` gives the previous close per stock; `ROW_NUMBER() ... DESC` picks the newest row per stock.
* **Q2** a `LATERAL` sub-query fetches the latest close for each holding.
* **Q4a** `HAVING COUNT(*) >= 2` filters *after* grouping; `WHERE` cannot see aggregates.
* **Q5** a window frame `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` = 7 trading days; shown only once a full 7-day window exists.

---

## 6. Assumptions
* One demo user (`DEMO_USER_ID`, default 1) and **no authentication** — out of scope for the brief.
* "Latest close" = the most recent `price_history` row of the stock. Seed data covers the 30 most recent **weekdays** ending today,
  so on a weekend the latest close is Friday's. Dates in the seed are relative to `CURRENT_DATE`, so the data never goes stale.
* Whole shares only; quantity 1 … 1,000,000. No fees, taxes, short-selling, fractional shares or order types other than market.
* Prices do not change while the app runs (the data is a static daily history), so P&L only moves when you trade.
* `users` 2–5 exist only to make the analytical queries meaningful (Q4b needs users with no orders); the app itself only uses user 1.
* Unknown symbol: 404 on `GET /stocks/{symbol}`, on watchlist calls and on `POST /orders`.
* The seed prices come from a deterministic pseudo-random walk, not real quotes.

## 7. Possible improvements (deliberately left out — "correctness over extra features")
Authentication and multiple users, a price-update job/WebSocket feed, limit/stop orders, realised P&L and fees, DB migrations (Alembic/Flyway),
a frontend test suite, Docker Compose, a pooled/async driver, and cursor-based pagination for very large order histories.

## 8. AI tool use
This project was built with the help of **Claude (Anthropic's AI assistant)**, which generated the first version of the code, the SQL,
the tests and this README. I reviewed it, ran it against PostgreSQL and I am prepared to walk through every query and make live changes
in the review call.
