"""
Order placement - the one place where money moves.

Business rules (from the brief):
  * market orders only, executed at the latest close
  * BUY needs enough wallet balance, SELL needs enough shares
  * wallet, holding and order row change together in ONE database transaction
  * average buy price is a weighted average
"""
from __future__ import annotations

from ..db import transaction
from ..errors import BusinessRuleError, NotFoundError
from ..repositories import holdings_repo, orders_repo, stocks_repo, users_repo
from .stock_service import pagination_meta


def place_order(user_id: int, symbol: str, side: str, quantity: int) -> dict:
    # Everything inside this block is atomic. Raising any exception (including our
    # BusinessRuleError) rolls back every statement that already ran.
    with transaction() as cur:
        stock = stocks_repo.get_quote(cur, symbol)
        if stock is None:
            raise NotFoundError(f"Stock '{symbol}' does not exist", code="STOCK_NOT_FOUND")

        price = stock["price"]                     # latest close = execution price
        total = price * quantity                   # Decimal * int -> exact, no float rounding

        # Lock the user row first. All orders of one user are therefore processed
        # one after another, which makes the balance / holding checks below race-free.
        user = users_repo.lock_user(cur, user_id)
        if user is None:
            raise NotFoundError("Demo user not found - did you run db/seed.sql?", code="USER_NOT_FOUND")

        if side == "BUY":
            if user["wallet_balance"] < total:
                raise BusinessRuleError(
                    f"Insufficient wallet balance: this order costs {total:.2f}, "
                    f"you have {user['wallet_balance']:.2f}",
                    code="INSUFFICIENT_FUNDS",
                    details={"required": total, "available": user["wallet_balance"]},
                )
            new_balance = users_repo.change_wallet(cur, user_id, -total)
            holdings_repo.add_shares(cur, user_id, stock["stock_id"], quantity, price)
        else:  # SELL
            holding = holdings_repo.get_for_update(cur, user_id, stock["stock_id"])
            owned = holding["quantity"] if holding else 0
            if owned < quantity:
                raise BusinessRuleError(
                    f"Insufficient holdings: you want to sell {quantity} {symbol} but own {owned}",
                    code="INSUFFICIENT_HOLDINGS",
                    details={"requested": quantity, "owned": owned},
                )
            new_balance = users_repo.change_wallet(cur, user_id, total)
            holdings_repo.remove_shares(cur, user_id, stock["stock_id"], quantity, owned)

        order = orders_repo.insert_order(cur, user_id, stock["stock_id"], side, quantity, price)

    return {
        "id": order["id"],
        "symbol": stock["symbol"],
        "name": stock["name"],
        "side": order["side"],
        "quantity": order["quantity"],
        "price": order["price"],
        "total_value": order["total_value"],
        "created_at": order["created_at"],
        "wallet_balance": new_balance,
    }


def list_orders(user_id: int, *, symbol, side, page: int, page_size: int) -> dict:
    with transaction() as cur:
        total = orders_repo.count_orders(cur, user_id, symbol, side)
        rows = orders_repo.list_orders(cur, user_id, symbol, side, page_size, (page - 1) * page_size)
    return {"data": rows, "pagination": pagination_meta(page, page_size, total)}
