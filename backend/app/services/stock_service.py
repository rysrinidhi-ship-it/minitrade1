from __future__ import annotations

import math

from ..db import transaction
from ..errors import NotFoundError
from ..repositories import stocks_repo

HISTORY_DAYS = 30


def pagination_meta(page: int, page_size: int, total: int) -> dict:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


def list_stocks(*, search, sector, sort, descending, page, page_size) -> dict:
    with transaction() as cur:
        total = stocks_repo.count_quotes(cur, search, sector)
        rows = stocks_repo.list_quotes(
            cur,
            search=search,
            sector=sector,
            sort=sort,
            descending=descending,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    return {"data": rows, "pagination": pagination_meta(page, page_size, total)}


def list_sectors() -> list[str]:
    with transaction() as cur:
        return stocks_repo.list_sectors(cur)


def get_stock_detail(symbol: str) -> dict:
    with transaction() as cur:
        stock = stocks_repo.get_quote(cur, symbol)
        if stock is None:
            raise NotFoundError(f"Stock '{symbol}' does not exist", code="STOCK_NOT_FOUND")
        history = stocks_repo.get_history(cur, stock.pop("stock_id"), HISTORY_DAYS)
    return {**stock, "history": history}
