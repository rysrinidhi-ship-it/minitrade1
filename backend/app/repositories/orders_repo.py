from __future__ import annotations


def insert_order(cur, user_id: int, stock_id: int, side: str, quantity: int, price) -> dict:
    cur.execute(
        """
        INSERT INTO orders (user_id, stock_id, side, quantity, price)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, side, quantity, price, quantity * price AS total_value, created_at
        """,
        (user_id, stock_id, side, quantity, price),
    )
    return cur.fetchone()


_FILTER = """
    WHERE o.user_id = %(user_id)s
      AND (%(symbol)s::text IS NULL OR s.symbol = %(symbol)s)
      AND (%(side)s::text   IS NULL OR o.side   = %(side)s)
"""


def count_orders(cur, user_id: int, symbol: str | None, side: str | None) -> int:
    cur.execute(
        f"SELECT COUNT(*) AS n FROM orders o JOIN stocks s ON s.id = o.stock_id {_FILTER}",
        {"user_id": user_id, "symbol": symbol, "side": side},
    )
    return cur.fetchone()["n"]


def list_orders(cur, user_id: int, symbol: str | None, side: str | None, limit: int, offset: int) -> list[dict]:
    """Newest first. `id DESC` is the tie-breaker so paging is stable."""
    cur.execute(
        f"""
        SELECT o.id, s.symbol, s.name, o.side, o.quantity, o.price,
               o.quantity * o.price AS total_value, o.created_at
        FROM orders o
        JOIN stocks s ON s.id = o.stock_id
        {_FILTER}
        ORDER BY o.created_at DESC, o.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"user_id": user_id, "symbol": symbol, "side": side, "limit": limit, "offset": offset},
    )
    return cur.fetchall()
