"""
One error type for the whole API and ONE JSON error shape:

    { "error": { "code": "INSUFFICIENT_FUNDS", "message": "...", "details": {...} } }

Services raise these exceptions; the handlers registered below turn them (and any
framework / unexpected error) into that shape, so the frontend only needs to
understand one format.
"""
from __future__ import annotations

from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    status = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class ValidationError(AppError):      # 400 - the request itself is malformed
    status = 400
    code = "VALIDATION_ERROR"


class NotFoundError(AppError):        # 404
    status = 404
    code = "NOT_FOUND"


class ConflictError(AppError):        # 409 - e.g. already in watchlist
    status = 409
    code = "CONFLICT"


class BusinessRuleError(AppError):    # 422 - well-formed request, but a trading rule says no
    status = 422
    code = "RULE_VIOLATION"


def error_body(code: str, message: str, details: Any = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return {"error": body}


_HTTP_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    415: "UNSUPPORTED_MEDIA_TYPE",
    500: "INTERNAL_ERROR",
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify(error_body(err.code, err.message, err.details)), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        status = err.code or 500
        code = _HTTP_CODES.get(status, "HTTP_ERROR")
        message = "The requested resource was not found" if status == 404 else (err.description or err.name)
        return jsonify(error_body(code, message)), status

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        # never leak internals (SQL, stack traces) to the client; log them instead
        app.logger.exception("Unhandled error: %s", err)
        return jsonify(error_body("INTERNAL_ERROR", "Something went wrong on our side")), 500
