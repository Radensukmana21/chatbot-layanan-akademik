from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.schedule import ScheduleItemResponse
from app.schemas.teacher import TeacherInformationResponse


ChatIntent = Literal[
    "jadwal_pelajaran",
    "informasi_guru",
]


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=1000,
    )

    conversation_id: UUID | None = None


class ChatEntitiesResponse(BaseModel):
    class_name: str | None = None
    day: str | None = None


class ChatScheduleDataResponse(BaseModel):
    academic_year: str
    items: list[ScheduleItemResponse]


class ChatTeacherDataResponse(BaseModel):
    academic_year: str
    search_mode: Literal["name", "subject"]
    query: str
    items: list[TeacherInformationResponse]


class ChatMessageResponse(BaseModel):
    conversation_id: UUID

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

    data: (
        ChatScheduleDataResponse
        | ChatTeacherDataResponse
        | None
    ) = None