"""
API tests against a REAL PostgreSQL database (no mocks for the data layer).

    export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/minitrade_test
    python -m unittest discover -s tests -v

WARNING: schema.sql is executed on that database (drops + recreates every table),
so point TEST_DATABASE_URL at a throw-away database, never at your real one.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from unittest import mock

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.repositories import users_repo  # noqa: E402

DB_DIR = ROOT.parent / "db"
TEST_URL = os.getenv("TEST_DATABASE_URL")
START_BALANCE = Decimal("100000.00")

app = None
LAST_SEED_DATE = None


def setUpModule():
    global app, LAST_SEED_DATE
    if not TEST_URL:
        raise unittest.SkipTest("set TEST_DATABASE_URL to run the API tests (database gets wiped!)")
    conn = psycopg2.connect(TEST_URL)
    conn.autocommit = True          # the .sql files manage their own BEGIN/COMMIT
    with conn.cursor() as cur:
        for name in ("schema.sql", "seed.sql"):
            cur.execute((DB_DIR / name).read_text(encoding="utf-8"))
        cur.execute("SELECT MAX(trade_date) FROM price_history")
        LAST_SEED_DATE = cur.fetchone()[0]
    conn.close()
    app = create_app(
        Settings(
            database_url=TEST_URL,
            cors_origins=("http://localhost:5173",),
            demo_user_id=1,
            default_page_size=20,
            max_page_size=100,
        )
    )


def tearDownModule():
    if app is not None:
        close_pool(app)


class ApiTestCase(unittest.TestCase):
    """Resets all mutable state before every test, so tests are independent."""

    def setUp(self):
        self.client = app.test_client()
        self.db = psycopg2.connect(TEST_URL)
        with self.db.cursor() as cur:
            cur.execute("TRUNCATE orders, holdings, watchlist RESTART IDENTITY")
            cur.execute("DELETE FROM price_history WHERE trade_date > %s", (LAST_SEED_DATE,))
            cur.execute("UPDATE users SET wallet_balance = %s", (START_BALANCE,))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # ---- helpers -------------------------------------------------------
    def q(self, sql, params=None):
        """Run a SELECT directly against the DB and return dict rows."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        self.db.rollback()  # end the read transaction so the next read sees fresh data
        return rows

    def wallet(self) -> Decimal:
        return self.q("SELECT wallet_balance FROM users WHERE id = 1")[0]["wallet_balance"]

    def price(self, symbol) -> Decimal:
        return Decimal(str(self.client.get(f"/api/stocks/{symbol}").get_json()["data"]["price"]))

    def order(self, symbol, side, quantity):
        return self.client.post("/api/orders", json={"symbol": symbol, "side": side, "quantity": quantity})

    def new_close(self, symbol, close: str):
        """Add a NEWER trading day for `symbol`, so the 'latest close' changes."""
        close = Decimal(close)
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO price_history (stock_id, trade_date, open, high, low, close, volume)
                SELECT id, %s, %s, %s, %s, %s, 1000 FROM stocks WHERE symbol = %s
                """,
                (LAST_SEED_DATE.fromordinal(LAST_SEED_DATE.toordinal() + 1), close, close, close, close, symbol),
            )
        self.db.commit()

    def assert_error(self, resp, status, code):
        self.assertEqual(resp.status_code, status, resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertEqual(set(body), {"error"})
        self.assertEqual(body["error"]["code"], code)
        self.assertTrue(body["error"]["message"])
        return body["error"]

    def assert_nothing_changed(self):
        self.assertEqual(self.wallet(), START_BALANCE)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM orders")[0]["n"], 0)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM holdings")[0]["n"], 0)


# ======================================================================
class StocksTests(ApiTestCase):
    def test_list_has_prices_and_pagination(self):
        r = self.client.get("/api/stocks")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(len(body["data"]), 14)
        self.assertEqual(body["pagination"], {"page": 1, "page_size": 20, "total": 14, "total_pages": 1})
        first = body["data"][0]
        self.assertEqual(
            set(first), {"symbol", "name", "sector", "as_of", "price", "prev_close", "change", "change_pct"}
        )
        self.assertEqual([s["symbol"] for s in body["data"]], sorted(s["symbol"] for s in body["data"]))

    def test_day_change_matches_last_two_closes(self):
        row = self.q(
            "SELECT close FROM price_history p JOIN stocks s ON s.id = p.stock_id "
            "WHERE s.symbol = 'TCS' ORDER BY trade_date DESC LIMIT 2"
        )
        last, prev = row[0]["close"], row[1]["close"]
        tcs = self.client.get("/api/stocks/TCS").get_json()["data"]
        self.assertEqual(Decimal(str(tcs["change"])), last - prev)
        expected_pct = ((last - prev) / prev * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(Decimal(str(tcs["change_pct"])), expected_pct)

    def test_search_name_symbol_and_wildcards_are_escaped(self):
        symbols = {s["symbol"] for s in self.client.get("/api/stocks?search=bank").get_json()["data"]}
        self.assertIn("HDFCBANK", symbols)
        self.assertIn("SBIN", symbols)  # matches name "State Bank of India"
        self.assertNotIn("TCS", symbols)
        self.assertEqual(self.client.get("/api/stocks?search=tcs").get_json()["pagination"]["total"], 1)
        # '%' and '_' are SQL wildcards - they must be treated as plain characters
        self.assertEqual(self.client.get("/api/stocks?search=%25").get_json()["pagination"]["total"], 0)
        self.assertEqual(self.client.get("/api/stocks?search=_").get_json()["pagination"]["total"], 0)

    def test_sector_filter_is_case_insensitive(self):
        data = self.client.get("/api/stocks?sector=it&sort=symbol").get_json()["data"]
        self.assertEqual([s["symbol"] for s in data], ["INFY", "TCS", "WIPRO"])

    def test_sectors_endpoint(self):
        sectors = self.client.get("/api/sectors").get_json()["data"]
        self.assertIn("Banking", sectors)
        self.assertEqual(sectors, sorted(sectors))

    def test_sorting(self):
        by_price = [s["price"] for s in self.client.get("/api/stocks?sort=price&order=desc").get_json()["data"]]
        self.assertEqual(by_price, sorted(by_price, reverse=True))
        by_change = [s["change_pct"] for s in self.client.get("/api/stocks?sort=change_pct&order=asc").get_json()["data"]]
        self.assertEqual(by_change, sorted(by_change))

    def test_pagination(self):
        p1 = self.client.get("/api/stocks?page=1&page_size=5").get_json()
        p3 = self.client.get("/api/stocks?page=3&page_size=5").get_json()
        p4 = self.client.get("/api/stocks?page=4&page_size=5").get_json()
        self.assertEqual(p1["pagination"], {"page": 1, "page_size": 5, "total": 14, "total_pages": 3})
        self.assertEqual(len(p1["data"]), 5)
        self.assertEqual(len(p3["data"]), 4)
        self.assertEqual(p4["data"], [])

    def test_invalid_query_params_return_400(self):
        for qs in ("sort=hack", "order=up", "page=0", "page=abc", "page_size=0", "page_size=101"):
            with self.subTest(qs=qs):
                self.assert_error(self.client.get(f"/api/stocks?{qs}"), 400, "VALIDATION_ERROR")

    def test_sql_injection_attempts_are_just_text(self):
        r = self.client.get("/api/stocks?search=%27%3B%20DROP%20TABLE%20stocks%3B--")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"], [])
        self.assertEqual(self.client.get("/api/stocks").get_json()["pagination"]["total"], 14)

    def test_detail_has_30_day_history_oldest_first(self):
        r = self.client.get("/api/stocks/tcs")  # lower case is accepted
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]
        self.assertEqual(data["symbol"], "TCS")
        hist = data["history"]
        self.assertEqual(len(hist), 30)
        self.assertEqual([h["date"] for h in hist], sorted(h["date"] for h in hist))
        self.assertEqual(set(hist[0]), {"date", "open", "high", "low", "close", "volume"})
        self.assertEqual(hist[-1]["close"], data["price"])

    def test_detail_unknown_symbol_is_404(self):
        self.assert_error(self.client.get("/api/stocks/NOPE"), 404, "STOCK_NOT_FOUND")


# ======================================================================
class WatchlistTests(ApiTestCase):
    def add(self, symbol):
        return self.client.post("/api/watchlist", json={"symbol": symbol})

    def test_add_list_remove(self):
        self.assertEqual(self.client.get("/api/watchlist").get_json()["data"], [])
        r = self.add("tcs")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["data"]["symbol"], "TCS")
        self.add("INFY")
        symbols = [s["symbol"] for s in self.client.get("/api/watchlist").get_json()["data"]]
        self.assertEqual(symbols, ["INFY", "TCS"])  # newest first
        self.assertEqual(self.client.delete("/api/watchlist/TCS").status_code, 204)
        symbols = [s["symbol"] for s in self.client.get("/api/watchlist").get_json()["data"]]
        self.assertEqual(symbols, ["INFY"])

    def test_duplicate_is_409(self):
        self.assertEqual(self.add("TCS").status_code, 201)
        self.assert_error(self.add("TCS"), 409, "ALREADY_IN_WATCHLIST")

    def test_remove_missing_is_404(self):
        self.assert_error(self.client.delete("/api/watchlist/TCS"), 404, "NOT_IN_WATCHLIST")
        self.assert_error(self.client.delete("/api/watchlist/NOPE"), 404, "STOCK_NOT_FOUND")

    def test_unknown_symbol_is_404(self):
        self.assert_error(self.add("NOPE"), 404, "STOCK_NOT_FOUND")

    def test_bad_payloads_are_400(self):
        for payload in ({}, {"symbol": 5}, {"symbol": ""}, {"symbol": "bad symbol!"}, [], "TCS"):
            with self.subTest(payload=payload):
                self.assert_error(self.client.post("/api/watchlist", json=payload), 400, "VALIDATION_ERROR")
        r = self.client.post("/api/watchlist", data="not json", content_type="application/json")
        self.assert_error(r, 400, "VALIDATION_ERROR")


# ======================================================================
class OrderTests(ApiTestCase):
    def test_buy_updates_wallet_holding_and_order(self):
        price = self.price("TCS")
        r = self.order("TCS", "BUY", 10)
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        data = r.get_json()["data"]
        self.assertEqual(Decimal(str(data["total_value"])), price * 10)
        self.assertEqual(Decimal(str(data["wallet_balance"])), START_BALANCE - price * 10)
        self.assertEqual(self.wallet(), START_BALANCE - price * 10)

        pf = self.client.get("/api/portfolio").get_json()["data"]
        self.assertEqual(len(pf["holdings"]), 1)
        h = pf["holdings"][0]
        self.assertEqual((h["symbol"], h["quantity"]), ("TCS", 10))
        self.assertEqual(Decimal(str(h["avg_buy_price"])), price)

    def test_side_is_case_insensitive_and_symbol_is_normalised(self):
        self.assertEqual(self.order(" tcs ", "buy", 1).status_code, 201)

    def test_average_buy_price_is_a_weighted_average(self):
        p1 = self.price("INFY")
        self.assertEqual(self.order("INFY", "BUY", 10).status_code, 201)
        self.new_close("INFY", "2000.00")                       # price moves up
        self.assertEqual(self.order("INFY", "BUY", 30).status_code, 201)

        # stored with 4 decimals, shown with 2 (same two roundings as the API)
        exact = (10 * p1 + 30 * Decimal("2000.00")) / 40
        expected = exact.quantize(Decimal("0.0001"), ROUND_HALF_UP).quantize(Decimal("0.01"), ROUND_HALF_UP)
        h = self.client.get("/api/portfolio").get_json()["data"]["holdings"][0]
        self.assertEqual(h["quantity"], 40)
        self.assertEqual(Decimal(str(h["avg_buy_price"])), expected)
        self.assertEqual(self.wallet(), START_BALANCE - 10 * p1 - 30 * Decimal("2000.00"))

    def test_sell_keeps_average_credits_wallet_at_latest_close(self):
        p1 = self.price("INFY")
        self.order("INFY", "BUY", 20)
        self.new_close("INFY", "1800.00")
        r = self.order("INFY", "SELL", 5)
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        self.assertEqual(self.wallet(), START_BALANCE - 20 * p1 + 5 * Decimal("1800.00"))
        h = self.client.get("/api/portfolio").get_json()["data"]["holdings"][0]
        self.assertEqual(h["quantity"], 15)
        self.assertEqual(Decimal(str(h["avg_buy_price"])), p1)   # selling does not change the average

    def test_selling_everything_removes_the_holding(self):
        self.order("SBIN", "BUY", 10)
        self.assertEqual(self.order("SBIN", "SELL", 10).status_code, 201)
        self.assertEqual(self.client.get("/api/portfolio").get_json()["data"]["holdings"], [])
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM holdings")[0]["n"], 0)
        # buying again starts a fresh average
        self.new_close("SBIN", "900.00")
        self.order("SBIN", "BUY", 2)
        h = self.client.get("/api/portfolio").get_json()["data"]["holdings"][0]
        self.assertEqual(Decimal(str(h["avg_buy_price"])), Decimal("900.00"))

    def test_insufficient_funds_is_422_and_changes_nothing(self):
        err = self.assert_error(self.order("MARUTI", "BUY", 100), 422, "INSUFFICIENT_FUNDS")
        self.assertIn("required", err["details"])
        self.assertIn("available", err["details"])
        self.assert_nothing_changed()

    def test_exact_balance_can_be_spent_but_not_one_paisa_more(self):
        price = self.price("SBIN")
        with self.db.cursor() as cur:
            cur.execute("UPDATE users SET wallet_balance = %s WHERE id = 1", (price * 3,))
        self.db.commit()
        self.assertEqual(self.order("SBIN", "BUY", 3).status_code, 201)
        self.assertEqual(self.wallet(), Decimal("0.00"))
        self.assert_error(self.order("SBIN", "BUY", 1), 422, "INSUFFICIENT_FUNDS")

    def test_sell_without_enough_shares_is_422_and_changes_nothing(self):
        err = self.assert_error(self.order("TCS", "SELL", 1), 422, "INSUFFICIENT_HOLDINGS")
        self.assertEqual(err["details"], {"requested": 1, "owned": 0})
        self.assert_nothing_changed()

        self.order("TCS", "BUY", 2)
        wallet_before = self.wallet()
        err = self.assert_error(self.order("TCS", "SELL", 3), 422, "INSUFFICIENT_HOLDINGS")
        self.assertEqual(err["details"], {"requested": 3, "owned": 2})
        self.assertEqual(self.wallet(), wallet_before)

    def test_invalid_input_is_400_with_field_details(self):
        bad = [
            {},
            {"symbol": "TCS", "side": "BUY"},                       # no quantity
            {"symbol": "TCS", "quantity": 1},                       # no side
            {"side": "BUY", "quantity": 1},                         # no symbol
            {"symbol": "TCS", "side": "HOLD", "quantity": 1},
            {"symbol": "TCS", "side": "BUY", "quantity": 0},
            {"symbol": "TCS", "side": "BUY", "quantity": -5},
            {"symbol": "TCS", "side": "BUY", "quantity": 1.5},
            {"symbol": "TCS", "side": "BUY", "quantity": "5"},
            {"symbol": "TCS", "side": "BUY", "quantity": True},
            {"symbol": "TCS", "side": "BUY", "quantity": 10**9},
            {"symbol": 123, "side": "BUY", "quantity": 1},
            {"symbol": "TCS; DROP", "side": "BUY", "quantity": 1},
            [],
            "BUY TCS",
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                err = self.assert_error(self.client.post("/api/orders", json=payload), 400, "VALIDATION_ERROR")
                if isinstance(payload, dict):
                    self.assertIn("fields", err["details"])
        r = self.client.post("/api/orders", data="{oops", content_type="application/json")
        self.assert_error(r, 400, "VALIDATION_ERROR")
        self.assert_nothing_changed()

    def test_all_field_errors_are_reported_together(self):
        err = self.assert_error(self.client.post("/api/orders", json={}), 400, "VALIDATION_ERROR")
        self.assertEqual(set(err["details"]["fields"]), {"symbol", "side", "quantity"})

    def test_unknown_symbol_is_404(self):
        self.assert_error(self.order("NOPE", "BUY", 1), 404, "STOCK_NOT_FOUND")
        self.assert_nothing_changed()

    def test_order_is_atomic_if_something_fails_midway(self):
        """Wallet debit + holding insert succeed, then the order insert blows up -> EVERYTHING is rolled back."""
        with mock.patch("app.services.order_service.orders_repo.insert_order", side_effect=RuntimeError("boom")):
            r = self.order("TCS", "BUY", 5)
        self.assert_error(r, 500, "INTERNAL_ERROR")
        self.assertNotIn("boom", r.get_data(as_text=True))       # internals are not leaked
        self.assert_nothing_changed()

    def test_concurrent_orders_can_never_overspend(self):
        """
        8 simultaneous BUYs, but the wallet only fits 3. A short sleep between 'check the
        balance' and 'debit the wallet' widens the race window: WITHOUT the row lock
        (SELECT ... FOR UPDATE) all 8 requests would pass the balance check together.
        """
        price = self.price("SBIN")
        qty = int(START_BALANCE // price // 3)                   # each order costs just under a third of the wallet
        results, barrier = [], threading.Barrier(8)
        real_change_wallet = users_repo.change_wallet

        def slow_change_wallet(*args, **kwargs):
            time.sleep(0.05)
            return real_change_wallet(*args, **kwargs)

        def worker():
            client = app.test_client()
            barrier.wait()                                        # start all requests at the same instant
            results.append(client.post("/api/orders", json={"symbol": "SBIN", "side": "BUY", "quantity": qty}).status_code)

        with mock.patch("app.services.order_service.users_repo.change_wallet", side_effect=slow_change_wallet):
            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(sorted(set(results)), [201, 422])
        self.assertEqual(results.count(201), 3)                  # exactly 3 fit into the wallet
        self.assertEqual(self.wallet(), START_BALANCE - 3 * qty * price)
        self.assertGreaterEqual(self.wallet(), 0)
        self.assertEqual(self.q("SELECT quantity FROM holdings")[0]["quantity"], 3 * qty)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM orders")[0]["n"], 3)

    def test_wallet_and_holdings_always_match_a_replay_of_the_order_log(self):
        """Independent check: replay every stored order in Python and compare with what the DB holds."""
        plan = [("TCS", "BUY", 3), ("INFY", "BUY", 7), ("TCS", "BUY", 2), ("INFY", "SELL", 4),
                ("TCS", "SELL", 5), ("WIPRO", "BUY", 40), ("INFY", "BUY", 1), ("WIPRO", "SELL", 15)]
        for i, (sym, side, qty) in enumerate(plan):
            if i in (2, 6):                                       # prices move between some trades
                self.new_close(sym, str(Decimal("1000.00") + 37 * i))
            r = self.order(sym, side, qty)
            self.assertEqual(r.status_code, 201, (sym, side, qty, r.get_data(as_text=True)))

        wallet, pos = START_BALANCE, {}
        for o in self.q("SELECT s.symbol, o.side, o.quantity, o.price FROM orders o JOIN stocks s ON s.id = o.stock_id ORDER BY o.id"):
            amount = o["quantity"] * o["price"]
            q0, a0 = pos.get(o["symbol"], (0, Decimal(0)))
            if o["side"] == "BUY":
                wallet -= amount
                a = ((q0 * a0 + o["quantity"] * o["price"]) / (q0 + o["quantity"])).quantize(Decimal("0.0001"), ROUND_HALF_UP)
                pos[o["symbol"]] = (q0 + o["quantity"], a)
            else:
                wallet += amount
                pos[o["symbol"]] = (q0 - o["quantity"], a0)
        pos = {k: v for k, v in pos.items() if v[0] > 0}

        self.assertEqual(self.wallet(), wallet)
        db = {r["symbol"]: (r["quantity"], r["avg_buy_price"]) for r in self.q(
            "SELECT s.symbol, h.quantity, h.avg_buy_price FROM holdings h JOIN stocks s ON s.id = h.stock_id")}
        self.assertEqual(db, pos)


# ======================================================================
class OrderHistoryTests(ApiTestCase):
    def seed_orders(self):
        for sym, side, qty in [("TCS", "BUY", 5), ("INFY", "BUY", 5), ("TCS", "SELL", 2), ("SBIN", "BUY", 10), ("INFY", "SELL", 1)]:
            self.assertEqual(self.order(sym, side, qty).status_code, 201)

    def test_empty(self):
        body = self.client.get("/api/orders").get_json()
        self.assertEqual(body["data"], [])
        self.assertEqual(body["pagination"]["total"], 0)

    def test_newest_first_and_pagination(self):
        self.seed_orders()
        p1 = self.client.get("/api/orders?page_size=2").get_json()
        self.assertEqual(p1["pagination"], {"page": 1, "page_size": 2, "total": 5, "total_pages": 3})
        self.assertEqual([o["id"] for o in p1["data"]], [5, 4])
        p3 = self.client.get("/api/orders?page_size=2&page=3").get_json()
        self.assertEqual([o["id"] for o in p3["data"]], [1])
        self.assertEqual(set(p1["data"][0]), {"id", "symbol", "name", "side", "quantity", "price", "total_value", "created_at"})

    def test_filters(self):
        self.seed_orders()
        sells = self.client.get("/api/orders?side=sell").get_json()
        self.assertEqual({o["side"] for o in sells["data"]}, {"SELL"})
        self.assertEqual(sells["pagination"]["total"], 2)
        tcs = self.client.get("/api/orders?symbol=tcs").get_json()
        self.assertEqual([o["id"] for o in tcs["data"]], [3, 1])
        both = self.client.get("/api/orders?symbol=TCS&side=BUY").get_json()
        self.assertEqual([o["id"] for o in both["data"]], [1])

    def test_invalid_params(self):
        for qs in ("side=HOLD", "page=0", "page_size=500", "symbol=bad%20symbol!"):
            with self.subTest(qs=qs):
                self.assert_error(self.client.get(f"/api/orders?{qs}"), 400, "VALIDATION_ERROR")


# ======================================================================
class PortfolioTests(ApiTestCase):
    def test_empty_portfolio(self):
        pf = self.client.get("/api/portfolio").get_json()["data"]
        self.assertEqual(pf["wallet_balance"], 100000.0)
        self.assertEqual(pf["holdings"], [])
        self.assertEqual((pf["invested_value"], pf["current_value"], pf["total_pnl"]), (0, 0, 0))
        self.assertEqual(pf["account_value"], 100000.0)

    def test_pnl_math(self):
        p_tcs, p_inf = self.price("TCS"), self.price("INFY")
        self.order("TCS", "BUY", 4)
        self.order("INFY", "BUY", 10)
        self.new_close("TCS", "4000.00")
        self.new_close("INFY", "1000.00")

        pf = self.client.get("/api/portfolio").get_json()["data"]
        inv = 4 * p_tcs + 10 * p_inf
        cur = 4 * Decimal("4000.00") + 10 * Decimal("1000.00")
        D = lambda x: Decimal(str(x))  # noqa: E731
        self.assertEqual(D(pf["invested_value"]), inv)
        self.assertEqual(D(pf["current_value"]), cur)
        self.assertEqual(D(pf["total_pnl"]), cur - inv)
        self.assertEqual(D(pf["total_pnl_pct"]), ((cur - inv) / inv * 100).quantize(Decimal("0.01"), ROUND_HALF_UP))
        self.assertEqual(D(pf["wallet_balance"]), START_BALANCE - inv)
        self.assertEqual(D(pf["account_value"]), START_BALANCE - inv + cur)

        tcs = next(h for h in pf["holdings"] if h["symbol"] == "TCS")
        self.assertEqual(D(tcs["current_price"]), Decimal("4000.00"))
        self.assertEqual(D(tcs["pnl"]), 4 * Decimal("4000.00") - 4 * p_tcs)
        # table rows add up to the totals shown above them
        self.assertEqual(sum(D(h["pnl"]) for h in pf["holdings"]), D(pf["total_pnl"]))


# ======================================================================
class PlatformTests(ApiTestCase):
    def test_cors_allows_the_frontend_origin_only(self):
        ok = self.client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(ok.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        bad = self.client.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", bad.headers)

    def test_preflight_request(self):
        r = self.client.options("/api/orders", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"})
        self.assertIn(r.status_code, (200, 204))
        self.assertIn("POST", r.headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", r.headers["Access-Control-Allow-Headers"])

    def test_framework_errors_use_the_same_json_shape(self):
        self.assert_error(self.client.get("/api/does-not-exist"), 404, "NOT_FOUND")
        self.assert_error(self.client.delete("/api/stocks"), 405, "METHOD_NOT_ALLOWED")
        self.assert_error(self.client.put("/api/orders", json={}), 405, "METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
