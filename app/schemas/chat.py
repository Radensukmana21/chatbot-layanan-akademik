from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.schedule import ScheduleItemResponse


class ChatMessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
    )


class ChatEntitiesResponse(BaseModel):
    class_name: str | None = None
    day: str | None = None


class ChatScheduleDataResponse(BaseModel):
    academic_year: str
    items: list[ScheduleItemResponse]


class ChatMessageResponse(BaseModel):
    intent: str | None
    intent_source: Literal["rule"] | None

    status: Literal[
        "answered",
        "needs_clarification",
        "invalid_request",
        "not_found",
        "unavailable",
        "unsupported",
    ]

    entities: ChatEntitiesResponse
    missing_entities: list[str]
    message: str
    data: ChatScheduleDataResponse | None = None