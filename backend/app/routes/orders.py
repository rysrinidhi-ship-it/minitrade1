from flask import Blueprint, current_app, jsonify, request

from ..services import order_service
from ..validators import (
    SIDES,
    parse_choice,
    parse_optional_symbol,
    parse_pagination,
    validate_order_payload,
)

bp = Blueprint("orders", __name__)


@bp.post("/orders")
def place_order():
    settings = current_app.config["SETTINGS"]
    symbol, side, quantity = validate_order_payload(request.get_json(force=True, silent=True))
    order = order_service.place_order(settings.demo_user_id, symbol, side, quantity)
    return jsonify({"data": order}), 201


@bp.get("/orders")
def list_orders():
    settings = current_app.config["SETTINGS"]
    args = request.args
    page, page_size = parse_pagination(args, settings.default_page_size, settings.max_page_size)
    side = parse_choice(args, "side", SIDES, "", lower=False) or None
    result = order_service.list_orders(
        settings.demo_user_id,
        symbol=parse_optional_symbol(args),
        side=side,
        page=page,
        page_size=page_size,
    )
    return jsonify(result)
