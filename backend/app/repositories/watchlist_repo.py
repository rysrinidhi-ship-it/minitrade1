from __future__ import annotations


def list_for_user(cur, user_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT q.symbol, q.name, q.sector, q.as_of,
               q.last_price AS price,
               q.prev_close,
               q.last_price - q.prev_close AS change,
               ROUND((q.last_price - q.prev_close) / q.prev_close * 100, 2) AS change_pct,
               w.created_at AS added_at
        FROM watchlist w
        JOIN v_stock_quotes q ON q.stock_id = w.stock_id
        WHERE w.user_id = %s
        ORDER BY w.created_at DESC, q.symbol
        """,
        (user_id,),
    )
    return cur.fetchall()


def add(cur, user_id: int, stock_id: int) -> dict | None:
    """Returns the new row, or None if it already existed (primary key says no)."""
    cur.execute(
        """
        INSERT INTO watchlist (user_id, stock_id) VALUES (%s, %s)
        ON CONFLICT (user_id, stock_id) DO NOTHING
        RETURNING created_at AS added_at
        """,
        (user_id, stock_id),
    )
    return cur.fetchone()


def remove(cur, user_id: int, stock_id: int) -> bool:
    cur.execute("DELETE FROM watchlist WHERE user_id = %s AND stock_id = %s", (user_id, stock_id))
    return cur.rowcount > 0
