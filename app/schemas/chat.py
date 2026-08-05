from __future__ import annotations

from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.extracurricular import (
    ExtracurricularResponse,
)
from app.schemas.schedule import ScheduleItemResponse
from app.schemas.teacher import TeacherInformationResponse


ChatIntent = Literal[
    "jadwal_pelajaran",
    "informasi_guru",
    "informasi_ekstrakurikuler",
    "ajukan_surat_izin",
    "cek_status_surat",
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


class ChatExtracurricularDataResponse(BaseModel):
    search_mode: Literal["list", "name"]

    focus: Literal[
        "general",
        "schedule",
        "advisor",
        "location",
    ]

    query: str | None = None
    items: list[ExtracurricularResponse]

class ChatPermissionStatusDataResponse(
    BaseModel
):
    tracking_code: str

    status: Literal[
        "pending",
        "approved",
        "rejected",
    ]

    submitted_at: datetime
    reviewed_at: datetime | None

class ChatPermissionSubmissionDataResponse(
    BaseModel
):
    tracking_code: str
    status: Literal["pending"]
    submitted_at: datetime

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
        | ChatExtracurricularDataResponse
        | ChatPermissionSubmissionDataResponse
        | ChatPermissionStatusDataResponse
        | None
    ) = None