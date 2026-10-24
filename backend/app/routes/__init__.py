from flask import Flask

from . import health, orders, portfolio, stocks, watchlist


def register_routes(app: Flask) -> None:
    for module in (health, stocks, watchlist, orders, portfolio):
        app.register_blueprint(module.bp, url_prefix="/api")
