-- =====================================================================
-- OPTIONAL demo trade history (run after seed.sql).
-- Gives users 1-3 a few past trades so Q2 / Q3 / the Portfolio screen have
-- something to show on first start. Users 4 and 5 deliberately never trade
-- (Q4b: "users who never placed an order").
--
-- Each order is executed at the close of the latest trading day on/before
-- its date, exactly like the live API does. Holdings and wallets are derived
-- from the orders so the three tables always agree.
-- Skip this file for a clean "Rs 1,00,000 and nothing else" start:
--     python scripts/init_db.py --clean
-- =====================================================================

BEGIN;

INSERT INTO orders (user_id, stock_id, side, quantity, price, created_at)
SELECT r.user_id, s.id, r.side, r.qty, px.close,
       (CURRENT_DATE - r.days_ago)::timestamp + r.hh * INTERVAL '1 hour'
FROM (VALUES
        -- user_id, symbol,      side,   qty, days_ago, hour of day
        (1, 'TCS',        'BUY',   3, 6, 10),
        (1, 'INFY',       'BUY',   8, 5, 11),
        (1, 'RELIANCE',   'BUY',   3, 4, 10),
        (1, 'TCS',        'BUY',   2, 3, 14),
        (1, 'INFY',       'SELL',  3, 2, 12),
        (1, 'HDFCBANK',   'BUY',   5, 1, 10),
        (2, 'SBIN',       'BUY',  40, 5, 11),
        (2, 'ITC',        'BUY',  60, 2, 15),
        (3, 'MARUTI',     'BUY',   2, 4, 12),
        (3, 'WIPRO',      'BUY',  50, 3, 10),
        (3, 'TCS',        'BUY',   4, 1, 13)
     ) AS r(user_id, symbol, side, qty, days_ago, hh)
JOIN stocks s ON s.symbol = r.symbol
JOIN LATERAL (
        SELECT p.close
        FROM price_history p
        WHERE p.stock_id = s.id
          AND p.trade_date <= CURRENT_DATE - r.days_ago
        ORDER BY p.trade_date DESC
        LIMIT 1
     ) px ON TRUE
ORDER BY r.days_ago DESC, r.hh;   -- oldest first => ids follow time

-- holdings = buys - sells; average cost = weighted average of the buys
-- (in this seed every SELL comes after all BUYs of that stock, so this equals
--  what the running-average logic in the API would have produced)
INSERT INTO holdings (user_id, stock_id, quantity, avg_buy_price)
SELECT user_id,
       stock_id,
       SUM(CASE side WHEN 'BUY' THEN quantity ELSE -quantity END),
       ROUND(SUM(CASE WHEN side = 'BUY' THEN quantity * price END)::numeric
             / SUM(CASE WHEN side = 'BUY' THEN quantity END), 4)
FROM orders
GROUP BY user_id, stock_id
HAVING SUM(CASE side WHEN 'BUY' THEN quantity ELSE -quantity END) > 0;

-- wallet = starting balance - net cash spent
UPDATE users u
SET wallet_balance = 100000.00 - COALESCE((
        SELECT SUM(CASE o.side WHEN 'BUY' THEN o.quantity * o.price
                               ELSE -(o.quantity * o.price) END)
        FROM orders o
        WHERE o.user_id = u.id
    ), 0);

COMMIT;

ANALYZE;
