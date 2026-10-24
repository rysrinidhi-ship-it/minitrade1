from flask import Blueprint, current_app, jsonify, request

from ..services import watchlist_service
from ..validators import validate_watchlist_payload

bp = Blueprint("watchlist", __name__)


def _user_id() -> int:
    # No login in this assignment: every request acts as the single demo user.
    return current_app.config["SETTINGS"].demo_user_id


@bp.get("/watchlist")
def get_watchlist():
    return jsonify({"data": watchlist_service.list_watchlist(_user_id())})


@bp.post("/watchlist")
def add_to_watchlist():
    symbol = validate_watchlist_payload(request.get_json(force=True, silent=True))
    return jsonify({"data": watchlist_service.add_to_watchlist(_user_id(), symbol)}), 201


@bp.delete("/watchlist/<symbol>")
def remove_from_watchlist(symbol: str):
    watchlist_service.remove_from_watchlist(_user_id(), symbol.strip().upper())
    return "", 204
