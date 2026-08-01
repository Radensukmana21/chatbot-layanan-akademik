from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def build_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


def check_database(database_url: str | None) -> dict[str, Any]:
    if not database_url:
        return {
            "status": "not_configured",
            "detail": "Database URL belum diatur.",
        }

    try:
        engine = build_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return {"status": "available"}
    except Exception as exc:
        # Jangan mengembalikan URL atau pesan driver yang dapat memuat credential.
        return {
            "status": "unavailable",
            "detail": exc.__class__.__name__,
        }
