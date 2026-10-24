from __future__ import annotations


def get_for_update(cur, user_id: int, stock_id: int) -> dict | None:
    cur.execute(
        "SELECT quantity, avg_buy_price FROM holdings WHERE user_id = %s AND stock_id = %s FOR UPDATE",
        (user_id, stock_id),
    )
    return cur.fetchone()


def add_shares(cur, user_id: int, stock_id: int, quantity: int, price) -> dict:
    """
    BUY: create the holding, or merge into the existing one with a WEIGHTED average:

        new_avg = (old_qty * old_avg + buy_qty * buy_price) / (old_qty + buy_qty)

    In an ON CONFLICT ... DO UPDATE the right-hand sides see the OLD row, so the
    quantity used inside the average is the quantity *before* this purchase.
    """
    cur.execute(
        """
        INSERT INTO holdings (user_id, stock_id, quantity, avg_buy_price)
        VALUES (%(user_id)s, %(stock_id)s, %(quantity)s, %(price)s)
        ON CONFLICT (user_id, stock_id) DO UPDATE
        SET avg_buy_price = ROUND(
                (holdings.quantity * holdings.avg_buy_price + EXCLUDED.quantity * EXCLUDED.avg_buy_price)
                / (holdings.quantity + EXCLUDED.quantity), 4),
            quantity      = holdings.quantity + EXCLUDED.quantity,
            updated_at    = now()
        RETURNING quantity, avg_buy_price
        """,
        {"user_id": user_id, "stock_id": stock_id, "quantity": quantity, "price": price},
    )
    return cur.fetchone()


def remove_shares(cur, user_id: int, stock_id: int, quantity: int, owned: int) -> None:
    """
    SELL: the average buy price does not change when you sell. If everything is sold
    the row is deleted (the table forbids quantity = 0), so a later buy starts fresh.
    """
    if quantity == owned:
        cur.execute("DELETE FROM holdings WHERE user_id = %s AND stock_id = %s", (user_id, stock_id))
    else:
        cur.execute(
            """
            UPDATE holdings SET quantity = quantity - %s, updated_at = now()
            WHERE user_id = %s AND stock_id = %s
            """,
            (quantity, user_id, stock_id),
        )


def list_positions(cur, user_id: int) -> list[dict]:
    """Every holding valued at the latest close. P&L = current value - invested (same rounded numbers the UI shows)."""
    cur.execute(
        """
        WITH pos AS (
            SELECT q.symbol, q.name, q.sector, h.quantity,
                   ROUND(h.avg_buy_price, 2)                  AS avg_buy_price,
                   q.last_price                               AS current_price,
                   ROUND(h.quantity * h.avg_buy_price, 2)     AS invested,
                   ROUND(h.quantity * q.last_price, 2)        AS current_value
            FROM holdings h
            JOIN v_stock_quotes q ON q.stock_id = h.stock_id
            WHERE h.user_id = %s
        )
        SELECT pos.*,
               current_value - invested AS pnl,
               ROUND((current_value - invested) / invested * 100, 2) AS pnl_pct
        FROM pos
        ORDER BY symbol
        """,
        (user_id,),
    )
    return cur.fetchall()
