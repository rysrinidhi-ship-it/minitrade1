from flask import Blueprint, current_app, jsonify

from ..services import portfolio_service

bp = Blueprint("portfolio", __name__)


@bp.get("/portfolio")
def get_portfolio():
    user_id = current_app.config["SETTINGS"].demo_user_id
    return jsonify({"data": portfolio_service.get_portfolio(user_id)})
