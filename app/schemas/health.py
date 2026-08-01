from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    application: str
    environment: str


class DatabaseCheck(BaseModel):
    status: Literal["available", "unavailable", "not_configured"]
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    academic_database: DatabaseCheck
    chatbot_database: DatabaseCheck
    auto_retrain_enabled: bool
