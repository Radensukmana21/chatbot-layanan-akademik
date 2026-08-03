from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(
    value: str | None,
    default: bool = False,
) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _as_positive_int(
    value: str | None,
    *,
    default: int,
    variable_name: str,
) -> int:
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{variable_name} harus berupa bilangan bulat."
        ) from exc

    if parsed < 1:
        raise ValueError(
            f"{variable_name} harus minimal 1."
        )

    return parsed


def _origins(
    value: str | None,
) -> tuple[str, ...]:
    if not value:
        return (
            "http://localhost",
            "http://127.0.0.1",
        )

    return tuple(
        origin.strip()
        for origin in value.split(",")
        if origin.strip()
    )


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

    chat_message_retention_days: int
    auto_retrain_enabled: bool


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv(
            "APP_NAME",
            "Chatbot Layanan Akademik",
        ),
        app_env=os.getenv(
            "APP_ENV",
            "development",
        ),
        app_host=os.getenv(
            "APP_HOST",
            "127.0.0.1",
        ),
        app_port=int(
            os.getenv("APP_PORT", "9000")
        ),
        app_debug=_as_bool(
            os.getenv("APP_DEBUG"),
            default=True,
        ),
        allowed_origins=_origins(
            os.getenv("ALLOWED_ORIGINS")
        ),
        academic_database_url=(
            os.getenv("ACADEMIC_DATABASE_URL")
            or None
        ),
        chatbot_database_url=(
            os.getenv("CHATBOT_DATABASE_URL")
            or None
        ),
        chat_message_retention_days=(
            _as_positive_int(
                os.getenv(
                    "CHAT_MESSAGE_RETENTION_DAYS"
                ),
                default=30,
                variable_name=(
                    "CHAT_MESSAGE_RETENTION_DAYS"
                ),
            )
        ),
        auto_retrain_enabled=_as_bool(
            os.getenv("AUTO_RETRAIN_ENABLED"),
            default=False,
        ),
    )