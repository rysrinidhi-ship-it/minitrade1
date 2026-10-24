-- =====================================================================
-- MiniTrade seed data (all prices are SYNTHETIC - no real market data)
--   * 5 users (user 1 is the demo user used by the app), each with Rs 1,00,000
--   * 14 stocks, each with 30 trading days (weekdays) of OHLC ending today
--   * a few watchlist rows
-- Prices come from a deterministic pseudo-random walk (md5-based), so every
-- run produces the same shape, only the dates move with CURRENT_DATE.
-- Run after schema.sql:  psql "$DATABASE_URL" -f db/seed.sql
-- =====================================================================

BEGIN;

INSERT INTO users (name, email) VALUES
    ('Demo Trader',  'demo@minitrade.test'),
    ('Aarav Sharma', 'aarav@minitrade.test'),
    ('Diya Patel',   'diya@minitrade.test'),
    ('Rohan Mehta',  'rohan@minitrade.test'),
    ('Ananya Iyer',  'ananya@minitrade.test');

INSERT INTO stocks (symbol, name, sector) VALUES
    ('RELIANCE',   'Reliance Industries',        'Energy'),
    ('TCS',        'Tata Consultancy Services',  'IT'),
    ('INFY',       'Infosys',                    'IT'),
    ('WIPRO',      'Wipro',                      'IT'),
    ('HDFCBANK',   'HDFC Bank',                  'Banking'),
    ('ICICIBANK',  'ICICI Bank',                 'Banking'),
    ('SBIN',       'State Bank of India',        'Banking'),
    ('ITC',        'ITC Limited',                'FMCG'),
    ('HINDUNILVR', 'Hindustan Unilever',         'FMCG'),
    ('LT',         'Larsen & Toubro',            'Infrastructure'),
    ('BHARTIARTL', 'Bharti Airtel',              'Telecom'),
    ('MARUTI',     'Maruti Suzuki India',        'Auto'),
    ('SUNPHARMA',  'Sun Pharmaceutical',         'Pharma'),
    ('ASIANPAINT', 'Asian Paints',               'Materials');

-- ---------------------------------------------------------------------
-- 30 days of OHLC per stock
--   u1..u5 = reproducible pseudo-random numbers in [0,1) from md5(symbol+date)
--   close  = base * exp(running sum of ln(1 + daily return))   (random walk, +-2.5%/day)
--   open   = previous close with a small gap, high/low wrap around open & close
-- ---------------------------------------------------------------------
INSERT INTO price_history (stock_id, trade_date, open, high, low, close, volume)
WITH base(symbol, base_price) AS (
    VALUES ('RELIANCE', 2450.00), ('TCS', 3800.00), ('INFY', 1500.00), ('WIPRO', 480.00),
           ('HDFCBANK', 1650.00), ('ICICIBANK', 1100.00), ('SBIN', 780.00),
           ('ITC', 430.00), ('HINDUNILVR', 2400.00), ('LT', 3500.00),
           ('BHARTIARTL', 1550.00), ('MARUTI', 11800.00), ('SUNPHARMA', 1700.00),
           ('ASIANPAINT', 2900.00)
),
days AS (   -- the latest 30 weekdays up to (and including) today
    SELECT d
    FROM (
        SELECT g::date AS d
        FROM generate_series(CURRENT_DATE - 60, CURRENT_DATE, INTERVAL '1 day') AS g
        WHERE EXTRACT(ISODOW FROM g) < 6
        ORDER BY g DESC
        LIMIT 30
    ) t
),
rnd AS (
    SELECT s.id AS stock_id, s.symbol, b.base_price, dy.d,
           ('x' || substr(md5(s.symbol || dy.d::text || 'a'), 1, 8))::bit(32)::bigint / 4294967296.0 AS u1,
           ('x' || substr(md5(s.symbol || dy.d::text || 'b'), 1, 8))::bit(32)::bigint / 4294967296.0 AS u2,
           ('x' || substr(md5(s.symbol || dy.d::text || 'c'), 1, 8))::bit(32)::bigint / 4294967296.0 AS u3,
           ('x' || substr(md5(s.symbol || dy.d::text || 'd'), 1, 8))::bit(32)::bigint / 4294967296.0 AS u4,
           ('x' || substr(md5(s.symbol || dy.d::text || 'e'), 1, 8))::bit(32)::bigint / 4294967296.0 AS u5
    FROM stocks s
    JOIN base b ON b.symbol = s.symbol
    CROSS JOIN days dy
),
closes AS (
    SELECT r.*,
           ROUND((r.base_price * EXP(SUM(LN(1 + (r.u1 - 0.5) * 0.05))
                                     OVER (PARTITION BY r.stock_id ORDER BY r.d)))::numeric, 2) AS close
    FROM rnd r
),
opens AS (
    SELECT c.*,
           ROUND((COALESCE(LAG(c.close) OVER (PARTITION BY c.stock_id ORDER BY c.d), c.base_price)
                  * (1 + (c.u2 - 0.5) * 0.01))::numeric, 2) AS open
    FROM closes c
)
SELECT stock_id,
       d,
       open,
       ROUND(GREATEST(open, close) * (1 + u3 * 0.008), 2) AS high,
       ROUND(LEAST(open, close)    * (1 - u4 * 0.008), 2) AS low,
       close,
       (300000 + u5 * 2700000)::bigint                    AS volume
FROM opens;

-- ---------------------------------------------------------------------
-- watchlists (TCS and RELIANCE end up on 3 lists, INFY on 2, ...)
-- ---------------------------------------------------------------------
INSERT INTO watchlist (user_id, stock_id)
SELECT w.user_id, s.id
FROM (VALUES
        (1, 'TCS'), (1, 'RELIANCE'), (1, 'INFY'),
        (2, 'TCS'), (2, 'HDFCBANK'), (2, 'RELIANCE'),
        (3, 'TCS'), (3, 'SBIN'),
        (4, 'INFY'), (4, 'MARUTI')
     ) AS w(user_id, symbol)
JOIN stocks s ON s.symbol = w.symbol;

COMMIT;

ANALYZE;
