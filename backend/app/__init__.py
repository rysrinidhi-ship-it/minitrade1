"""
MiniTrade API - application factory.

Layers (each only talks to the one below it):
    routes/        HTTP in/out: parse + validate the request, call a service, build the response
    services/      business rules + transactions (what the app *does*)
    repositories/  SQL only (how data is read/written)
"""
from __future__ import annotations

import logging

from flask import Flask, request

from .config import Settings
from .errors import register_error_handlers
from .json_provider import AppJSONProvider
from .routes import register_routes


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    app.json = AppJSONProvider(app)
    app.url_map.strict_slashes = False
    app.config["SETTINGS"] = settings or Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    register_error_handlers(app)
    register_routes(app)

    @app.after_request
    def add_cors_headers(response):
        # Browsers block the React dev server (another origin) from calling the API
        # unless the API says so. Allowed origins come from the CORS_ORIGINS env var.
        allowed = app.config["SETTINGS"].cors_origins
        origin = request.headers.get("Origin")
        if origin and ("*" in allowed or origin in allowed):
            response.headers["Access-Control-Allow-Origin"] = "*" if "*" in allowed else origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
        return response

    return app
