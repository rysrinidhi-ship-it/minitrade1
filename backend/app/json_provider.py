"""JSON encoding rules: Decimal -> number, dates -> ISO-8601, keep field order."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


class AppJSONProvider(DefaultJSONProvider):
    sort_keys = False

    @staticmethod
    def default(o):
        # All money maths happens in the database / with Decimal. Only at this very
        # last step (the HTTP response) do we turn a value into a JSON number.
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (dt.datetime, dt.date)):
            return o.isoformat()
        return DefaultJSONProvider.default(o)
