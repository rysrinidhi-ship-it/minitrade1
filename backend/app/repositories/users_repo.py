from __future__ import annotations


def get_wallet(cur, user_id: int) -> dict | None:
    cur.execute("SELECT id, name, wallet_balance FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def lock_user(cur, user_id: int) -> dict | None:
    """
    SELECT ... FOR UPDATE takes a row lock on the user. A second order from the same
    user waits here until the first transaction commits/rolls back, and then sees the
    NEW balance - this is what stops two simultaneous orders from overspending.
    """
    cur.execute(
        "SELECT id, name, wallet_balance FROM users WHERE id = %s FOR UPDATE", (user_id,)
    )
    return cur.fetchone()


def change_wallet(cur, user_id: int, delta) -> object:
    """Add `delta` (negative to debit) and return the new balance."""
    cur.execute(
        "UPDATE users SET wallet_balance = wallet_balance + %s WHERE id = %s RETURNING wallet_balance",
        (delta, user_id),
    )
    return cur.fetchone()["wallet_balance"]
