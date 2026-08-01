from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.schedule import ScheduleItemResponse


ChatIntent = Literal["jadwal_pelajaran"]


class ChatContextPayload(BaseModel):
    intent: ChatIntent | None = None
    class_name: str | None = None
    day: str | None = None
    is_active: bool = False


class ChatMessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
    )

    context: ChatContextPayload | None = None


class ChatEntitiesResponse(BaseModel):
    class_name: str | None = None
    day: str | None = None


class ChatScheduleDataResponse(BaseModel):
    academic_year: str
    items: list[ScheduleItemResponse]


class ChatMessageResponse(BaseModel):
    intent: ChatIntent | None
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

    # Context ini dikirim kembali oleh frontend pada pesan berikutnya.
    context: ChatContextPayload