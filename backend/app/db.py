"""
Database access: a small connection pool + a `transaction()` helper.

    with transaction() as cur:
        ...several statements...

Everything inside the `with` block is ONE database transaction: it is committed
when the block ends normally and rolled back if any exception escapes (including
our own business-rule errors). Repositories receive the cursor, never a connection,
so they cannot commit by accident.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from flask import current_app
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

_lock = threading.Lock()


def _pool() -> ThreadedConnectionPool:
    pools = current_app.extensions.setdefault("db", {})
    if "pool" not in pools:
        with _lock:
            if "pool" not in pools:
                pools["pool"] = ThreadedConnectionPool(
                    1, 10, current_app.config["SETTINGS"].database_url
                )
    return pools["pool"]


@contextmanager
def transaction():
    pool = _pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pool(app) -> None:
    pool = app.extensions.get("db", {}).pop("pool", None)
    if pool is not None:
        pool.closeall()
