from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.chatbot_models import ChatbotBase
from app.models import (
    AcademicYear,
    Base,
    SchoolClass,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from app.repositories.permission_request_repository import (
    PermissionRequestRepository,
)
from app.services.permission_conversation import (
    process_permission_draft_input,
    start_permission_conversation,
)


@pytest.fixture
def engines():
    academic_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    chatbot_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        academic_engine
    )
    ChatbotBase.metadata.create_all(
        chatbot_engine
    )

    with Session(academic_engine) as session:
        academic_year = AcademicYear(
            name="2025/2026",
            start_date=date(2025, 7, 1),
            end_date=date(2026, 6, 30),
            is_active=True,
        )

        session.add(academic_year)
        session.flush()

        session.add(
            SchoolClass(
                academic_year_id=academic_year.id,
                class_name="7A",
                grade=7,
                group_letter="A",
                is_active=True,
            )
        )

        session.commit()

    try:
        yield academic_engine, chatbot_engine
    finally:
        Base.metadata.drop_all(
            academic_engine
        )
        ChatbotBase.metadata.drop_all(
            chatbot_engine
        )

        academic_engine.dispose()
        chatbot_engine.dispose()


def create_conversation_id(
    chatbot_session: Session,
) -> str:
    conversation = ConversationRepository(
        chatbot_session
    ).create()

    chatbot_session.flush()

    return conversation.id


def process_message(
    *,
    conversation_id: str,
    message: str,
    chatbot_session: Session,
    academic_session: Session,
    now: datetime,
):
    return process_permission_draft_input(
        conversation_id=conversation_id,
        message=message,
        draft_repository=(
            PermissionDraftRepository(
                chatbot_session
            )
        ),
        permission_repository=(
            PermissionRequestRepository(
                academic_session
            )
        ),
        now=now,
    )


def test_completes_permission_draft_flow(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        start_result = (
            start_permission_conversation(
                conversation_id=conversation_id,
                draft_repository=(
                    PermissionDraftRepository(
                        chatbot_session
                    )
                ),
                now=now,
            )
        )

        assert start_result.status == "needs_input"
        assert start_result.draft is not None
        assert (
            start_result.draft.step
            == "student_name"
        )

        name_result = process_message(
            conversation_id=conversation_id,
            message="Siswa Contoh",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert name_result.status == "needs_input"
        assert name_result.draft is not None
        assert (
            name_result.draft.step
            == "class_name"
        )

        class_result = process_message(
            conversation_id=conversation_id,
            message="kelas 7A",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert class_result.status == "needs_input"
        assert class_result.draft is not None
        assert class_result.draft.class_name == "7A"
        assert (
            class_result.draft.step
            == "permission_type"
        )

        type_result = process_message(
            conversation_id=conversation_id,
            message="Sakit",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert type_result.status == "needs_input"
        assert type_result.draft is not None
        assert (
            type_result.draft.permission_type
            == "sakit"
        )
        assert (
            type_result.draft.step
            == "description"
        )

        description_result = process_message(
            conversation_id=conversation_id,
            message=(
                "Tidak dapat mengikuti pelajaran."
            ),
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert (
            description_result.status
            == "needs_input"
        )
        assert description_result.draft is not None
        assert (
            description_result.draft.step
            == "phone_number"
        )

        phone_result = process_message(
            conversation_id=conversation_id,
            message="lewati",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert (
            phone_result.status
            == "ready_for_confirmation"
        )
        assert phone_result.draft is not None
        assert phone_result.draft.phone_number is None
        assert (
            phone_result.draft.step
            == "confirmation"
        )
        assert (
            phone_result.draft.awaiting_confirmation
            is True
        )

        confirmation_result = process_message(
            conversation_id=conversation_id,
            message="YA",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert (
            confirmation_result.status
            == "confirmed"
        )
        assert (
            confirmation_result.should_submit
            is True
        )
        assert confirmation_result.draft is not None


def test_rejects_invalid_class_format(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        draft_repository = (
            PermissionDraftRepository(
                chatbot_session
            )
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=draft_repository,
            now=now,
        )

        process_message(
            conversation_id=conversation_id,
            message="Siswa Contoh",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        result = process_message(
            conversation_id=conversation_id,
            message="7Z",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert result.status == "invalid_input"
        assert result.draft is not None
        assert result.draft.step == "class_name"


def test_rejects_unknown_active_class(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=(
                PermissionDraftRepository(
                    chatbot_session
                )
            ),
            now=now,
        )

        process_message(
            conversation_id=conversation_id,
            message="Siswa Contoh",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        result = process_message(
            conversation_id=conversation_id,
            message="8A",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert result.status == "invalid_input"
        assert "tidak ditemukan" in (
            result.message.lower()
        )


def test_rejects_invalid_permission_type(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=(
                PermissionDraftRepository(
                    chatbot_session
                )
            ),
            now=now,
        )

        process_message(
            conversation_id=conversation_id,
            message="Siswa Contoh",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        process_message(
            conversation_id=conversation_id,
            message="7A",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        result = process_message(
            conversation_id=conversation_id,
            message="Liburan",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert result.status == "invalid_input"
        assert result.draft is not None
        assert (
            result.draft.step
            == "permission_type"
        )


def test_rejects_invalid_phone_number(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=(
                PermissionDraftRepository(
                    chatbot_session
                )
            ),
            now=now,
        )

        for message in [
            "Siswa Contoh",
            "7A",
            "Sakit",
            "Tidak dapat mengikuti pelajaran.",
        ]:
            process_message(
                conversation_id=conversation_id,
                message=message,
                chatbot_session=chatbot_session,
                academic_session=academic_session,
                now=now,
            )

        result = process_message(
            conversation_id=conversation_id,
            message="nomor-salah",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert result.status == "invalid_input"
        assert result.draft is not None
        assert (
            result.draft.step
            == "phone_number"
        )


def test_cancels_permission_draft(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        draft_repository = (
            PermissionDraftRepository(
                chatbot_session
            )
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=draft_repository,
            now=now,
        )

        result = process_message(
            conversation_id=conversation_id,
            message="batal",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now,
        )

        assert result.status == "cancelled"
        assert result.draft is None

        assert (
            draft_repository.get_active(
                conversation_id=conversation_id,
                now=now,
            )
            is None
        )


def test_returns_expired_for_old_draft(
    engines,
) -> None:
    academic_engine, chatbot_engine = engines
    now = datetime(2026, 8, 5, 10, 0)

    with (
        Session(academic_engine) as academic_session,
        Session(chatbot_engine) as chatbot_session,
    ):
        conversation_id = create_conversation_id(
            chatbot_session
        )

        start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=(
                PermissionDraftRepository(
                    chatbot_session
                )
            ),
            now=now,
        )

        result = process_message(
            conversation_id=conversation_id,
            message="Siswa Contoh",
            chatbot_session=chatbot_session,
            academic_session=academic_session,
            now=now + timedelta(minutes=31),
        )

        assert result.status == "expired"
        assert result.draft is None