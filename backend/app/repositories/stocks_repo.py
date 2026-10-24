"""SQL for stocks and prices. Every function receives a cursor and only runs queries."""
from __future__ import annotations

# ORDER BY cannot take bind parameters, so the allowed sort keys are whitelisted here.
# Only these constant strings ever reach the SQL text - user input never does.
SORT_COLUMNS = {
    "symbol": "q.symbol",
    "name": "q.name",
    "sector": "q.sector",
    "price": "q.last_price",
    "change_pct": "change_pct",
}

_QUOTE_COLUMNS = """
    q.symbol, q.name, q.sector, q.as_of,
    q.last_price                                                  AS price,
    q.prev_close,
    q.last_price - q.prev_close                                   AS change,
    ROUND((q.last_price - q.prev_close) / q.prev_close * 100, 2)  AS change_pct
"""

_FILTER = r"""
    WHERE (%(pattern)s::text IS NULL
           OR q.symbol ILIKE %(pattern)s ESCAPE '\'
           OR q.name   ILIKE %(pattern)s ESCAPE '\')
      AND (%(sector)s::text IS NULL OR LOWER(q.sector) = LOWER(%(sector)s))
"""


def _like_pattern(search: str | None) -> str | None:
    if not search:
        return None
    escaped = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


def count_quotes(cur, search: str | None, sector: str | None) -> int:
    cur.execute(
        f"SELECT COUNT(*) AS n FROM v_stock_quotes q {_FILTER}",
        {"pattern": _like_pattern(search), "sector": sector},
    )
    return cur.fetchone()["n"]


def list_quotes(cur, *, search, sector, sort: str, descending: bool, limit: int, offset: int) -> list[dict]:
    order_col = SORT_COLUMNS[sort]                      # KeyError impossible: validated upstream
    direction = "DESC" if descending else "ASC"
    cur.execute(
        f"""
        SELECT {_QUOTE_COLUMNS}
        FROM v_stock_quotes q
        {_FILTER}
        ORDER BY {order_col} {direction} NULLS LAST, q.symbol ASC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"pattern": _like_pattern(search), "sector": sector, "limit": limit, "offset": offset},
    )
    return cur.fetchall()


def list_sectors(cur) -> list[str]:
    cur.execute("SELECT DISTINCT sector FROM stocks ORDER BY sector")
    return [r["sector"] for r in cur.fetchall()]


def get_quote(cur, symbol: str) -> dict | None:
    """Latest price + day change for one symbol (None if unknown). Includes stock_id."""
    cur.execute(
        f"""
        SELECT q.stock_id, {_QUOTE_COLUMNS}
        FROM v_stock_quotes q
        WHERE q.symbol = %s
        """,
        (symbol,),
    )
    return cur.fetchone()


def get_history(cur, stock_id: int, days: int = 30) -> list[dict]:
    """Newest `days` rows, returned oldest -> newest (chart order)."""
    cur.execute(
        """
        SELECT trade_date AS date, open, high, low, close, volume
        FROM (
            SELECT trade_date, open, high, low, close, volume
            FROM price_history
            WHERE stock_id = %s
            ORDER BY trade_date DESC
            LIMIT %s
        ) recent
        ORDER BY trade_date ASC
        """,
        (stock_id, days),
    )
    return cur.fetchall()
