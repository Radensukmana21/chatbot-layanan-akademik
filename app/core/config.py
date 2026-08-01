from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # API masih bisa menjalankan /health sebelum dependency terpasang.
    def load_dotenv(*args, **kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://localhost", "http://127.0.0.1")
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    app_host: str
    app_port: int
    app_debug: bool
    allowed_origins: tuple[str, ...]
    academic_database_url: str | None
    chatbot_database_url: str | None
    auto_retrain_enabled: bool


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Chatbot Layanan Akademik"),
        app_env=os.getenv("APP_ENV", "development"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "9000")),
        app_debug=_as_bool(os.getenv("APP_DEBUG"), default=True),
        allowed_origins=_origins(os.getenv("ALLOWED_ORIGINS")),
        academic_database_url=os.getenv("ACADEMIC_DATABASE_URL") or None,
        chatbot_database_url=os.getenv("CHATBOT_DATABASE_URL") or None,
        auto_retrain_enabled=_as_bool(os.getenv("AUTO_RETRAIN_ENABLED"), default=False),
    )
