from __future__ import annotations

from ..db import transaction
from ..errors import ConflictError, NotFoundError
from ..repositories import stocks_repo, watchlist_repo


def _stock_or_404(cur, symbol: str) -> dict:
    stock = stocks_repo.get_quote(cur, symbol)
    if stock is None:
        raise NotFoundError(f"Stock '{symbol}' does not exist", code="STOCK_NOT_FOUND")
    return stock


def list_watchlist(user_id: int) -> list[dict]:
    with transaction() as cur:
        return watchlist_repo.list_for_user(cur, user_id)


def add_to_watchlist(user_id: int, symbol: str) -> dict:
    with transaction() as cur:
        stock = _stock_or_404(cur, symbol)
        row = watchlist_repo.add(cur, user_id, stock["stock_id"])
        if row is None:
            raise ConflictError(f"{symbol} is already in your watchlist", code="ALREADY_IN_WATCHLIST")
        stock.pop("stock_id")
        return {**stock, "added_at": row["added_at"]}


def remove_from_watchlist(user_id: int, symbol: str) -> None:
    with transaction() as cur:
        stock = _stock_or_404(cur, symbol)
        if not watchlist_repo.remove(cur, user_id, stock["stock_id"]):
            raise NotFoundError(f"{symbol} is not in your watchlist", code="NOT_IN_WATCHLIST")
