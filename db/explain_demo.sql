-- =====================================================================
-- EXPLAIN before / after an index  (referenced from the README)
-- Everything happens inside a transaction that is ROLLED BACK at the end,
-- so your data and indexes are untouched afterwards.
--
--   psql "$DATABASE_URL" -f db/explain_demo.sql
--
-- Query under test = the "Orders" screen: newest 20 orders of one user.
-- ---------------------------------------------------------------------
BEGIN;

-- 1. make the table big enough for the planner to care (1,000 users, 400k orders)
INSERT INTO users (name, email)
SELECT 'Load user ' || g, 'load' || g || '@minitrade.test'
FROM generate_series(1, 1000) g;

INSERT INTO orders (user_id, stock_id, side, quantity, price, created_at)
SELECT 1 + (g % 1005),                         -- spread over user ids 1..1005
       1 + (g % 14),                           -- the 14 seeded stocks
       CASE WHEN g % 3 = 0 THEN 'SELL' ELSE 'BUY' END,
       1 + (g % 50),
       100 + (g % 900),
       now() - (g % 400000) * INTERVAL '1 minute'
FROM generate_series(1, 400000) g;

-- 2. BEFORE: remove the index that serves this query
DROP INDEX idx_orders_user_created;
ANALYZE orders;

\echo '===== BEFORE: no (user_id, created_at) index ====='
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id, stock_id, side, quantity, price, created_at
FROM orders
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 20;

-- 3. AFTER: add the composite index (equality column first, sort column second)
CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC);
ANALYZE orders;

\echo '===== AFTER: index on (user_id, created_at DESC) ====='
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id, stock_id, side, quantity, price, created_at
FROM orders
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 20;

ROLLBACK;
