"""
Input validation helpers (HTTP layer). They turn raw query strings / JSON bodies
into clean Python values or raise ValidationError (-> HTTP 400).
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .errors import ValidationError

SYMBOL_RE = re.compile(r"^[A-Z0-9&.\-]{1,20}$")
SIDES = ("BUY", "SELL")
MAX_ORDER_QUANTITY = 100_000


def parse_pagination(args: Mapping[str, str], default_size: int, max_size: int) -> tuple[int, int]:
    page = _int_arg(args, "page", default=1, minimum=1)
    page_size = _int_arg(args, "page_size", default=default_size, minimum=1, maximum=max_size)
    return page, page_size


def _int_arg(args, name, *, default, minimum=None, maximum=None) -> int:
    raw = args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError(f"'{name}' must be an integer", details={"field": name}) from None
    if minimum is not None and value < minimum:
        raise ValidationError(f"'{name}' must be >= {minimum}", details={"field": name})
    if maximum is not None and value > maximum:
        raise ValidationError(f"'{name}' must be <= {maximum}", details={"field": name})
    return value


def parse_choice(args: Mapping[str, str], name: str, allowed: tuple[str, ...], default: str, *, lower=True) -> str:
    raw = args.get(name)
    if raw is None or raw == "":
        return default
    value = raw.lower() if lower else raw.upper()
    if value not in allowed:
        raise ValidationError(
            f"'{name}' must be one of: {', '.join(allowed)}", details={"field": name, "allowed": list(allowed)}
        )
    return value


def parse_optional_text(args: Mapping[str, str], name: str, max_len: int = 50) -> str | None:
    raw = args.get(name)
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    if len(raw) > max_len:
        raise ValidationError(f"'{name}' is too long (max {max_len} characters)", details={"field": name})
    return raw


def parse_optional_symbol(args: Mapping[str, str], name: str = "symbol") -> str | None:
    raw = parse_optional_text(args, name, 20)
    if raw is None:
        return None
    raw = raw.upper()
    if not SYMBOL_RE.match(raw):
        raise ValidationError(f"'{name}' is not a valid stock symbol", details={"field": name})
    return raw


def require_json_object(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    return payload


def _check_symbol(value: Any, errors: dict) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors["symbol"] = "is required and must be a non-empty string"
        return None
    symbol = value.strip().upper()
    if not SYMBOL_RE.match(symbol):
        errors["symbol"] = "is not a valid stock symbol"
        return None
    return symbol


def validate_watchlist_payload(payload: Any) -> str:
    body = require_json_object(payload)
    errors: dict[str, str] = {}
    symbol = _check_symbol(body.get("symbol"), errors)
    if errors:
        raise ValidationError("Invalid input", details={"fields": errors})
    return symbol  # type: ignore[return-value]


def validate_order_payload(payload: Any) -> tuple[str, str, int]:
    """Returns (symbol, side, quantity). Collects *all* field errors before failing."""
    body = require_json_object(payload)
    errors: dict[str, str] = {}

    symbol = _check_symbol(body.get("symbol"), errors)

    side = body.get("side")
    if not isinstance(side, str) or side.strip().upper() not in SIDES:
        errors["side"] = "must be either BUY or SELL"
        side = None
    else:
        side = side.strip().upper()

    quantity = body.get("quantity")
    # bool is a subclass of int in Python, so exclude it explicitly (true != 1 share)
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        errors["quantity"] = "must be a whole number"
        quantity = None
    elif quantity <= 0:
        errors["quantity"] = "must be greater than 0"
        quantity = None
    elif quantity > MAX_ORDER_QUANTITY:
        errors["quantity"] = f"must be at most {MAX_ORDER_QUANTITY}"
        quantity = None

    if errors:
        raise ValidationError("Invalid input", details={"fields": errors})
    return symbol, side, quantity  # type: ignore[return-value]
