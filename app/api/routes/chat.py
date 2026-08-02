from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_academic_session,
    get_chatbot_session,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
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
    academic_session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
    chatbot_session: Annotated[
        Session,
        Depends(get_chatbot_session),
    ],
) -> ChatMessageResponse:
    conversation_repository = ConversationRepository(
        chatbot_session
    )

    if payload.conversation_id is None:
        conversation = conversation_repository.create()
    else:
        conversation = conversation_repository.get_by_id(
            str(payload.conversation_id)
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "conversation_not_found",
                    "message": (
                        "Percakapan tidak ditemukan. "
                        "Mulai percakapan baru tanpa "
                        "conversation_id."
                    ),
                },
            )

    request_context = conversation_repository.load_context(
        conversation
    )

    result = handle_chat_message(
        message=payload.message,
        class_repository=SchoolClassRepository(
            academic_session
        ),
        schedule_repository=LessonScheduleRepository(
            academic_session
        ),
        context=request_context,
    )

    conversation_repository.save_context(
        conversation,
        result.context,
    )

    try:
        chatbot_session.commit()
    except Exception:
        chatbot_session.rollback()
        raise

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
        conversation_id=conversation.id,
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