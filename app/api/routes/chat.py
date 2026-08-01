from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_academic_session
from app.repositories.lesson_schedule_repository import (
    LessonScheduleRepository,
)
from app.repositories.school_class_repository import (
    SchoolClassRepository,
)
from app.schemas.chat import (
    ChatEntitiesResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatScheduleDataResponse,
)
from app.schemas.schedule import ScheduleItemResponse
from app.services.chat_service import handle_chat_message


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)


@router.post(
    "/messages",
    response_model=ChatMessageResponse,
)
def create_chat_message(
    payload: ChatMessageRequest,
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
) -> ChatMessageResponse:
    result = handle_chat_message(
        message=payload.message,
        class_repository=SchoolClassRepository(session),
        schedule_repository=LessonScheduleRepository(session),
    )

    data: ChatScheduleDataResponse | None = None

    if (
        result.status == "answered"
        and result.academic_year is not None
    ):
        data = ChatScheduleDataResponse(
            academic_year=result.academic_year,
            items=[
                ScheduleItemResponse.model_validate(item)
                for item in result.items
            ],
        )

    return ChatMessageResponse(
        intent=result.intent,
        intent_source=result.intent_source,
        status=result.status,
        entities=ChatEntitiesResponse(
            class_name=result.class_name,
            day=result.day,
        ),
        missing_entities=list(result.missing_entities),
        message=result.message,
        data=data,
    )