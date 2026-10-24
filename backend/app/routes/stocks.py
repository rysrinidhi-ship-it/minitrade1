from flask import Blueprint, current_app, jsonify, request

from ..repositories.stocks_repo import SORT_COLUMNS
from ..services import stock_service
from ..validators import parse_choice, parse_optional_text, parse_pagination

bp = Blueprint("stocks", __name__)


@bp.get("/stocks")
def list_stocks():
    settings = current_app.config["SETTINGS"]
    args = request.args
    page, page_size = parse_pagination(args, settings.default_page_size, settings.max_page_size)
    sort = parse_choice(args, "sort", tuple(SORT_COLUMNS), "symbol")
    order = parse_choice(args, "order", ("asc", "desc"), "asc")
    result = stock_service.list_stocks(
        search=parse_optional_text(args, "search", 50),
        sector=parse_optional_text(args, "sector", 60),
        sort=sort,
        descending=(order == "desc"),
        page=page,
        page_size=page_size,
    )
    return jsonify(result)


@bp.get("/sectors")
def list_sectors():
    return jsonify({"data": stock_service.list_sectors()})


@bp.get("/stocks/<symbol>")
def stock_detail(symbol: str):
    return jsonify({"data": stock_service.get_stock_detail(symbol.strip().upper())})
