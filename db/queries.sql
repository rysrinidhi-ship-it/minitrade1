-- =====================================================================
-- MiniTrade - Part A queries (plain PostgreSQL)
-- Run all:  psql "$DATABASE_URL" -f db/queries.sql
-- =====================================================================


-- ---------------------------------------------------------------------
-- Q1. Top 5 gainers by % change vs previous close
--     LAG() looks at the previous trading day of the SAME stock
--     (PARTITION BY stock_id). ROW_NUMBER() marks the newest row per stock.
--     The filter rn = 1 is applied in the outer query, after LAG has seen
--     the full history of each stock.
-- ---------------------------------------------------------------------
WITH ranked AS (
    SELECT stock_id,
           trade_date,
           close,
           LAG(close) OVER (PARTITION BY stock_id ORDER BY trade_date)       AS prev_close,
           ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY trade_date DESC) AS rn
    FROM price_history
)
SELECT s.symbol,
       s.name,
       r.trade_date,
       r.prev_close,
       r.close                                                    AS last_close,
       ROUND((r.close - r.prev_close) / r.prev_close * 100, 2)    AS pct_change
FROM ranked r
JOIN stocks s ON s.id = r.stock_id
WHERE r.rn = 1
  AND r.prev_close IS NOT NULL
ORDER BY pct_change DESC
LIMIT 5;


-- ---------------------------------------------------------------------
-- Q2. Holdings of user 1: quantity, average price, current price, unrealised P&L
--     "Current price" = latest close, fetched with a LATERAL sub-query
--     (one index look-up per holding).
-- ---------------------------------------------------------------------
SELECT s.symbol,
       s.name,
       h.quantity,
       ROUND(h.avg_buy_price, 2)                               AS avg_buy_price,
       cur.close                                               AS current_price,
       ROUND(h.quantity * h.avg_buy_price, 2)                  AS invested,
       ROUND(h.quantity * cur.close, 2)                        AS current_value,
       ROUND(h.quantity * (cur.close - h.avg_buy_price), 2)    AS unrealised_pnl,
       ROUND((cur.close - h.avg_buy_price) / h.avg_buy_price * 100, 2) AS unrealised_pnl_pct
FROM holdings h
JOIN stocks s ON s.id = h.stock_id
JOIN LATERAL (
        SELECT p.close
        FROM price_history p
        WHERE p.stock_id = h.stock_id
        ORDER BY p.trade_date DESC
        LIMIT 1
     ) cur ON TRUE
WHERE h.user_id = 1
ORDER BY s.symbol;


-- ---------------------------------------------------------------------
-- Q3. Total traded value per day for the last 7 days (today included)
--     generate_series gives one row for every day, so days without any
--     order show 0 instead of disappearing (that is why it is a LEFT JOIN).
--     The join condition is a range on created_at (not created_at::date),
--     so the index on created_at-based columns stays usable.
-- ---------------------------------------------------------------------
SELECT d::date                              AS trade_day,
       COUNT(o.id)                          AS orders_placed,
       COALESCE(SUM(o.quantity * o.price), 0) AS total_traded_value
FROM generate_series(CURRENT_DATE - 6, CURRENT_DATE, INTERVAL '1 day') AS d
LEFT JOIN orders o
       ON o.created_at >= d
      AND o.created_at <  d + INTERVAL '1 day'
GROUP BY d
ORDER BY d;


-- ---------------------------------------------------------------------
-- Q4a. Most-watchlisted stocks (GROUP BY + HAVING)
--      HAVING filters AFTER grouping (it can use COUNT(*)); WHERE cannot.
--      Only stocks that are on at least 2 watchlists are shown.
-- ---------------------------------------------------------------------
SELECT s.symbol,
       s.name,
       COUNT(*) AS watchlisted_by
FROM watchlist w
JOIN stocks s ON s.id = w.stock_id
GROUP BY s.id, s.symbol, s.name
HAVING COUNT(*) >= 2
ORDER BY watchlisted_by DESC, s.symbol;


-- ---------------------------------------------------------------------
-- Q4b. Users who never placed an order (LEFT JOIN ... IS NULL anti-join)
--      Every user is kept by the LEFT JOIN; users without orders get NULLs
--      in the orders columns, and we keep exactly those rows.
-- ---------------------------------------------------------------------
SELECT u.id, u.name, u.email
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE o.id IS NULL
ORDER BY u.id;


-- ---------------------------------------------------------------------
-- Q5. 7-day moving average of the closing price for one stock (TCS)
--     The window is "this row and the 6 before it" (7 trading days).
--     For the first 6 days there are fewer than 7 rows, so we return NULL
--     instead of an average over a partial window.
-- ---------------------------------------------------------------------
SELECT p.trade_date,
       p.close,
       CASE WHEN COUNT(*) OVER w = 7
            THEN ROUND(AVG(p.close) OVER w, 2)
       END AS moving_avg_7d
FROM price_history p
JOIN stocks s ON s.id = p.stock_id
WHERE s.symbol = 'TCS'
WINDOW w AS (ORDER BY p.trade_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY p.trade_date;
