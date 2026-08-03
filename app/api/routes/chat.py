from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import (
    get_academic_session,
    get_chatbot_session,
)
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
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
from app.repositories.teacher_repository import (
    TeacherRepository,
)
from app.schemas.chat import (
    ChatEntitiesResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatScheduleDataResponse,
    ChatTeacherDataResponse,
)
from app.schemas.schedule import ScheduleItemResponse
from app.schemas.teacher import TeacherInformationResponse
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
    message_repository = ConversationMessageRepository(
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

    settings = get_settings()
    retention_days = settings.chat_message_retention_days

    message_repository.add_user_message(
        conversation_id=conversation.id,
        content=payload.message,
        retention_days=retention_days,
    )

    result = handle_chat_message(
        message=payload.message,
        class_repository=SchoolClassRepository(
            academic_session
        ),
        schedule_repository=LessonScheduleRepository(
            academic_session
        ),
        teacher_repository=TeacherRepository(
            academic_session
        ),
        context=request_context,
    )

    conversation_repository.save_context(
        conversation,
        result.context,
    )

    message_repository.add_assistant_message(
        conversation_id=conversation.id,
        content=result.message,
        intent=result.intent,
        intent_source=result.intent_source,
        response_status=result.status,
        class_name=result.class_name,
        day=result.day,
        retention_days=retention_days,
    )

    try:
        chatbot_session.commit()
    except Exception:
        chatbot_session.rollback()
        raise

    data: (
        ChatScheduleDataResponse
        | ChatTeacherDataResponse
        | None
    ) = None

    if (
        result.intent == "jadwal_pelajaran"
        and result.status == "answered"
        and result.academic_year is not None
    ):
        data = ChatScheduleDataResponse(
            academic_year=result.academic_year,
            items=[
                ScheduleItemResponse.model_validate(item)
                for item in result.items
            ],
        )

    elif (
        result.intent == "informasi_guru"
        and result.status == "answered"
        and result.academic_year is not None
        and result.teacher_search_mode is not None
        and result.teacher_query is not None
    ):
        teacher_items = [
            TeacherInformationResponse(
                id=item.id,
                name=item.name,
                subjects=list(item.subjects),
                classes=list(item.classes),
            )
            for item in result.teacher_items
        ]

        data = ChatTeacherDataResponse(
            academic_year=result.academic_year,
            search_mode=result.teacher_search_mode,
            query=result.teacher_query,
            items=teacher_items,
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