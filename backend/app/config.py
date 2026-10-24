"""Configuration comes only from environment variables (optionally via a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    demo_user_id: int
    default_page_size: int
    max_page_size: int

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        return cls(
            database_url=os.getenv(
                "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/minitrade"
            ),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
            demo_user_id=_int("DEMO_USER_ID", 1),
            default_page_size=_int("DEFAULT_PAGE_SIZE", 20),
            max_page_size=_int("MAX_PAGE_SIZE", 100),
        )
