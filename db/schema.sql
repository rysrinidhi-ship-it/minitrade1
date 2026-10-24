-- =====================================================================
-- MiniTrade schema (PostgreSQL 13+)
-- Money is always NUMERIC (never FLOAT). Prices have 2 decimals,
-- average buy price keeps 4 decimals so weighted averages don't drift.
-- Run:  psql "$DATABASE_URL" -f db/schema.sql
-- =====================================================================

DROP VIEW  IF EXISTS v_stock_quotes;
DROP TABLE IF EXISTS orders        CASCADE;
DROP TABLE IF EXISTS holdings      CASCADE;
DROP TABLE IF EXISTS watchlist     CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS stocks        CASCADE;
DROP TABLE IF EXISTS users         CASCADE;

-- ---------------------------------------------------------------------
-- users: one demo user in the app, a few extra rows exist only so the
-- analytical queries (e.g. "users who never placed an order") are meaningful.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id             SERIAL        PRIMARY KEY,
    name           VARCHAR(100)  NOT NULL,
    email          VARCHAR(255)  NOT NULL UNIQUE,
    wallet_balance NUMERIC(14,2) NOT NULL DEFAULT 100000.00
                   CONSTRAINT chk_wallet_non_negative CHECK (wallet_balance >= 0),
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- stocks: static instrument data
-- ---------------------------------------------------------------------
CREATE TABLE stocks (
    id      SERIAL       PRIMARY KEY,
    symbol  VARCHAR(20)  NOT NULL UNIQUE,
    name    VARCHAR(150) NOT NULL,
    sector  VARCHAR(60)  NOT NULL
);
CREATE INDEX idx_stocks_sector ON stocks (sector);

-- ---------------------------------------------------------------------
-- price_history: one OHLC row per stock per trading day
-- UNIQUE (stock_id, trade_date) doubles as the index used to find the
-- latest / previous close of a stock quickly.
-- ---------------------------------------------------------------------
CREATE TABLE price_history (
    id         BIGSERIAL     PRIMARY KEY,
    stock_id   INTEGER       NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    trade_date DATE          NOT NULL,
    open       NUMERIC(12,2) NOT NULL CHECK (open  > 0),
    high       NUMERIC(12,2) NOT NULL CHECK (high  > 0),
    low        NUMERIC(12,2) NOT NULL CHECK (low   > 0),
    close      NUMERIC(12,2) NOT NULL CHECK (close > 0),
    volume     BIGINT        NOT NULL DEFAULT 0 CHECK (volume >= 0),
    CONSTRAINT uq_price_stock_date UNIQUE (stock_id, trade_date),
    CONSTRAINT chk_ohlc_consistent CHECK (
        high >= low AND high >= open AND high >= close
                    AND low  <= open AND low  <= close
    )
);
CREATE INDEX idx_price_history_date ON price_history (trade_date);

-- ---------------------------------------------------------------------
-- watchlist: many-to-many between users and stocks.
-- Composite PK makes "already in watchlist" a database guarantee (-> 409).
-- ---------------------------------------------------------------------
CREATE TABLE watchlist (
    user_id    INTEGER     NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    stock_id   INTEGER     NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, stock_id)
);
-- PK covers lookups by user; this one serves "most watchlisted stock" (GROUP BY stock_id)
CREATE INDEX idx_watchlist_stock ON watchlist (stock_id);

-- ---------------------------------------------------------------------
-- orders: immutable trade log (market orders executed at the latest close).
-- price is copied onto the order, because the stock price keeps changing.
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    id         BIGSERIAL     PRIMARY KEY,
    user_id    INTEGER       NOT NULL REFERENCES users(id)  ON DELETE RESTRICT,
    stock_id   INTEGER       NOT NULL REFERENCES stocks(id) ON DELETE RESTRICT,
    side       VARCHAR(4)    NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity   INTEGER       NOT NULL CHECK (quantity > 0),
    price      NUMERIC(12,2) NOT NULL CHECK (price > 0),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- order history screen: "my orders, newest first"
CREATE INDEX idx_orders_user_created  ON orders (user_id, created_at DESC);
-- per-stock analytics
CREATE INDEX idx_orders_stock_created ON orders (stock_id, created_at DESC);

-- ---------------------------------------------------------------------
-- holdings: current position per user+stock (derived from orders but kept
-- as a table so the portfolio screen doesn't replay the whole order log).
-- Rows with quantity 0 are deleted by the application.
-- avg_buy_price is the weighted average cost of the shares still held.
-- ---------------------------------------------------------------------
CREATE TABLE holdings (
    user_id       INTEGER       NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    stock_id      INTEGER       NOT NULL REFERENCES stocks(id) ON DELETE RESTRICT,
    quantity      INTEGER       NOT NULL CHECK (quantity > 0),
    avg_buy_price NUMERIC(14,4) NOT NULL CHECK (avg_buy_price > 0),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, stock_id)
);

-- ---------------------------------------------------------------------
-- v_stock_quotes: latest close + previous close for every stock.
-- LATERAL + the (stock_id, trade_date) unique index means each stock costs
-- two index look-ups instead of a scan over the whole price history.
-- ---------------------------------------------------------------------
CREATE VIEW v_stock_quotes AS
SELECT s.id        AS stock_id,
       s.symbol,
       s.name,
       s.sector,
       last.trade_date AS as_of,
       last.close      AS last_price,
       prev.close      AS prev_close
FROM stocks s
JOIN LATERAL (
        SELECT p.trade_date, p.close
        FROM price_history p
        WHERE p.stock_id = s.id
        ORDER BY p.trade_date DESC
        LIMIT 1
     ) last ON TRUE
LEFT JOIN LATERAL (
        SELECT p.close
        FROM price_history p
        WHERE p.stock_id = s.id
        ORDER BY p.trade_date DESC
        OFFSET 1 LIMIT 1
     ) prev ON TRUE;
