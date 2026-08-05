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
from app.repositories.extracurricular_repository import (
    ExtracurricularRepository,
)
from app.repositories.permission_request_repository import (
    PermissionRequestRepository,
)
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from app.schemas.chat import (
    ChatEntitiesResponse,
    ChatExtracurricularDataResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatPermissionStatusDataResponse,
    ChatPermissionSubmissionDataResponse,
    ChatScheduleDataResponse,
    ChatTeacherDataResponse,
)
from app.schemas.schedule import ScheduleItemResponse
from app.schemas.teacher import TeacherInformationResponse
from app.schemas.extracurricular import (
    ExtracurricularResponse,
    ExtracurricularScheduleResponse,
)
from app.services.chat_service import (
    ChatContext,
    handle_chat_message,
)
from app.services.permission_chat_flow import (
    handle_permission_submission_chat,
)


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
    permission_repository = (
        PermissionRequestRepository(
            academic_session
        )
    )
    draft_repository = PermissionDraftRepository(
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

    permission_flow = (
        handle_permission_submission_chat(
            conversation_id=conversation.id,
            message=payload.message,
            draft_repository=draft_repository,
            permission_repository=(
                permission_repository
            ),
        )
    )

    regular_result = None

    if permission_flow is not None:
        response_intent = "ajukan_surat_izin"
        response_intent_source = "rule"
        response_status = permission_flow.status
        response_message = permission_flow.message
        response_class_name = None
        response_day = None
        response_missing_entities = list(
            permission_flow.missing_entities
        )

        response_context = ChatContext(
            intent="ajukan_surat_izin",
            is_active=False,
        )

        storage_policy = "metadata_only"
    else:
        request_context = (
            conversation_repository.load_context(
                conversation
            )
        )

        regular_result = handle_chat_message(
            message=payload.message,
            class_repository=(
                SchoolClassRepository(
                    academic_session
                )
            ),
            schedule_repository=(
                LessonScheduleRepository(
                    academic_session
                )
            ),
            teacher_repository=(
                TeacherRepository(
                    academic_session
                )
            ),
            extracurricular_repository=(
                ExtracurricularRepository(
                    academic_session
                )
            ),
            permission_request_repository=(
                permission_repository
            ),
            context=request_context,
        )

        response_intent = regular_result.intent
        response_intent_source = (
            regular_result.intent_source
        )
        response_status = regular_result.status
        response_message = regular_result.message
        response_class_name = (
            regular_result.class_name
        )
        response_day = regular_result.day
        response_missing_entities = list(
            regular_result.missing_entities
        )
        response_context = (
            regular_result.context
        )

        storage_policy = "full"

    settings = get_settings()
    retention_days = (
        settings.chat_message_retention_days
    )

    message_repository.add_user_message(
        conversation_id=conversation.id,
        content=payload.message,
        storage_policy=storage_policy,
        retention_days=retention_days,
    )

    conversation_repository.save_context(
        conversation,
        response_context,
    )

    message_repository.add_assistant_message(
        conversation_id=conversation.id,
        content=response_message,
        intent=response_intent,
        intent_source=(
            response_intent_source
        ),
        response_status=response_status,
        class_name=response_class_name,
        day=response_day,
        storage_policy=storage_policy,
        retention_days=retention_days,
    )

    try:
        # Commit academic lebih dahulu karena hasil akhir
        # pengajuan berada pada database akademik.
        if (
            permission_flow is not None
            and permission_flow.request
            is not None
        ):
            academic_session.commit()
            academic_session.refresh(
                permission_flow.request
            )

        chatbot_session.commit()

    except Exception:
        academic_session.rollback()
        chatbot_session.rollback()
        raise

    data: (
        ChatScheduleDataResponse
        | ChatTeacherDataResponse
        | ChatExtracurricularDataResponse
        | ChatPermissionSubmissionDataResponse
        | ChatPermissionStatusDataResponse
        | None
    ) = None

    if permission_flow is not None:
        if permission_flow.request is not None:
            permission_request = (
                permission_flow.request
            )

            data = (
                ChatPermissionSubmissionDataResponse(
                    tracking_code=(
                        permission_request.tracking_code
                    ),
                    status="pending",
                    submitted_at=(
                        permission_request.submitted_at
                    ),
                )
            )

    elif regular_result is not None:
        if (
            regular_result.intent
            == "jadwal_pelajaran"
            and regular_result.status == "answered"
            and regular_result.academic_year
            is not None
        ):
            data = ChatScheduleDataResponse(
                academic_year=(
                    regular_result.academic_year
                ),
                items=[
                    ScheduleItemResponse.model_validate(
                        item
                    )
                    for item in regular_result.items
                ],
            )

        elif (
            regular_result.intent
            == "informasi_guru"
            and regular_result.status == "answered"
            and regular_result.academic_year
            is not None
            and regular_result.teacher_search_mode
            is not None
            and regular_result.teacher_query
            is not None
        ):
            data = ChatTeacherDataResponse(
                academic_year=(
                    regular_result.academic_year
                ),
                search_mode=(
                    regular_result.teacher_search_mode
                ),
                query=regular_result.teacher_query,
                items=[
                    TeacherInformationResponse(
                        id=item.id,
                        name=item.name,
                        subjects=list(
                            item.subjects
                        ),
                        classes=list(
                            item.classes
                        ),
                    )
                    for item in (
                        regular_result.teacher_items
                    )
                ],
            )

        elif (
            regular_result.intent
            == "informasi_ekstrakurikuler"
            and regular_result.status == "answered"
            and (
                regular_result
                .extracurricular_search_mode
                is not None
            )
            and (
                regular_result
                .extracurricular_focus
                is not None
            )
        ):
            data = ChatExtracurricularDataResponse(
                search_mode=(
                    regular_result
                    .extracurricular_search_mode
                ),
                focus=(
                    regular_result
                    .extracurricular_focus
                ),
                query=(
                    regular_result
                    .extracurricular_query
                ),
                items=[
                    ExtracurricularResponse(
                        id=item.id,
                        name=item.name,
                        advisor_name=(
                            item.advisor_name
                        ),
                        location=item.location,
                        description=(
                            item.description
                        ),
                        schedules=[
                            ExtracurricularScheduleResponse(
                                day=schedule.day,
                                start_time=(
                                    schedule.start_time
                                ),
                                end_time=(
                                    schedule.end_time
                                ),
                            )
                            for schedule in (
                                item.schedules
                            )
                        ],
                    )
                    for item in (
                        regular_result
                        .extracurricular_items
                    )
                ],
            )

        elif (
            regular_result.intent
            == "cek_status_surat"
            and regular_result.status == "answered"
            and (
                regular_result
                .permission_status_item
                is not None
            )
        ):
            status_item = (
                regular_result
                .permission_status_item
            )

            data = (
                ChatPermissionStatusDataResponse(
                    tracking_code=(
                        status_item.tracking_code
                    ),
                    status=status_item.status,
                    submitted_at=(
                        status_item.submitted_at
                    ),
                    reviewed_at=(
                        status_item.reviewed_at
                    ),
                )
            )

    return ChatMessageResponse(
        conversation_id=conversation.id,
        intent=response_intent,
        intent_source=response_intent_source,
        status=response_status,
        entities=ChatEntitiesResponse(
            class_name=response_class_name,
            day=response_day,
        ),
        missing_entities=(
            response_missing_entities
        ),
        message=response_message,
        data=data,
    )