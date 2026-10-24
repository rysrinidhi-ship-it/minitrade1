from __future__ import annotations

from decimal import Decimal

from ..db import transaction
from ..errors import NotFoundError
from ..repositories import holdings_repo, users_repo


def get_portfolio(user_id: int) -> dict:
    with transaction() as cur:
        user = users_repo.get_wallet(cur, user_id)
        if user is None:
            raise NotFoundError("Demo user not found - did you run db/seed.sql?", code="USER_NOT_FOUND")
        holdings = holdings_repo.list_positions(cur, user_id)

    invested = sum((h["invested"] for h in holdings), Decimal("0"))
    current_value = sum((h["current_value"] for h in holdings), Decimal("0"))
    total_pnl = current_value - invested
    return {
        "wallet_balance": user["wallet_balance"],
        "invested_value": invested,
        "current_value": current_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl / invested * 100, 2) if invested else Decimal("0"),
        "account_value": user["wallet_balance"] + current_value,   # cash + shares
        "holdings": holdings,
    }
