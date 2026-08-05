from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.chatbot_models import (
    ChatbotBase,
    ConversationMessage,
    PermissionDraft,
)
from app.core.dependencies import (
    get_academic_session,
    get_chatbot_session,
)
from app.main import app
from app.models import (
    AcademicYear,
    Base,
    PermissionRequest,
    SchoolClass,
)
from app.repositories.permission_request_repository import (
    PermissionRequestRepository,
)
from app.services.permission_request_service import (
    submit_permission_request,
)


@dataclass(frozen=True, slots=True)
class PermissionChatHarness:
    client: TestClient
    academic_engine: Engine
    chatbot_engine: Engine


@pytest.fixture
def harness() -> Generator[
    PermissionChatHarness,
    None,
    None,
]:
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

    def override_academic_session(
    ) -> Generator[Session, None, None]:
        with Session(academic_engine) as session:
            yield session

    def override_chatbot_session(
    ) -> Generator[Session, None, None]:
        with Session(chatbot_engine) as session:
            yield session

    app.dependency_overrides[
        get_academic_session
    ] = override_academic_session

    app.dependency_overrides[
        get_chatbot_session
    ] = override_chatbot_session

    try:
        with TestClient(app) as client:
            yield PermissionChatHarness(
                client=client,
                academic_engine=academic_engine,
                chatbot_engine=chatbot_engine,
            )
    finally:
        app.dependency_overrides.clear()

        Base.metadata.drop_all(
            academic_engine
        )

        ChatbotBase.metadata.drop_all(
            chatbot_engine
        )

        academic_engine.dispose()
        chatbot_engine.dispose()


def post_message(
    client: TestClient,
    message: str,
    *,
    conversation_id: str | None = None,
):
    payload: dict[str, object] = {
        "message": message,
    }

    if conversation_id is not None:
        payload["conversation_id"] = (
            conversation_id
        )

    return client.post(
        "/api/v1/chat/messages",
        json=payload,
    )


def complete_permission_flow(
    harness: PermissionChatHarness,
) -> tuple[str, dict[str, object]]:
    first_response = post_message(
        harness.client,
        "Saya ingin mengajukan surat izin",
    )

    assert first_response.status_code == 200

    first_payload = first_response.json()
    conversation_id = str(
        first_payload["conversation_id"]
    )

    messages = [
        "Siswa Privasi",
        "7A",
        "Sakit",
        (
            "Tidak dapat mengikuti pelajaran "
            "karena kondisi kesehatan."
        ),
        "081234000000",
        "YA",
    ]

    final_payload: dict[str, object] = (
        first_payload
    )

    for message in messages:
        response = post_message(
            harness.client,
            message,
            conversation_id=conversation_id,
        )

        assert response.status_code == 200
        final_payload = response.json()

    return conversation_id, final_payload


def test_permission_messages_are_metadata_only(
    harness: PermissionChatHarness,
) -> None:
    conversation_id, final_payload = (
        complete_permission_flow(harness)
    )

    assert (
        final_payload["status"]
        == "answered"
    )

    with Session(
        harness.chatbot_engine
    ) as session:
        messages = list(
            session.scalars(
                select(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id
                    == conversation_id
                )
                .order_by(
                    ConversationMessage.id
                )
            )
        )

    # Tujuh request pengguna dan tujuh respons bot.
    assert len(messages) == 14

    assert all(
        message.storage_policy
        == "metadata_only"
        for message in messages
    )

    stored_content = "\n".join(
        message.content.lower()
        for message in messages
    )

    # Nilai asli tidak boleh tersimpan di tabel pesan.
    assert "siswa privasi" not in stored_content

    assert (
        "kondisi kesehatan"
        not in stored_content
    )

    assert "081234000000" not in stored_content


def test_permission_draft_is_deleted_after_submit(
    harness: PermissionChatHarness,
) -> None:
    conversation_id, final_payload = (
        complete_permission_flow(harness)
    )

    with Session(
        harness.chatbot_engine
    ) as session:
        draft = session.get(
            PermissionDraft,
            conversation_id,
        )

    assert draft is None

    with Session(
        harness.academic_engine
    ) as session:
        request = session.scalar(
            select(PermissionRequest).where(
                PermissionRequest.source_key
                == (
                    "chat:permission:"
                    f"{conversation_id}"
                )
            )
        )

    assert request is not None

    assert (
        request.tracking_code
        == final_payload["data"][
            "tracking_code"
        ]
    )

    assert request.status == "pending"


def test_cancel_deletes_draft_and_creates_no_request(
    harness: PermissionChatHarness,
) -> None:
    first_payload = post_message(
        harness.client,
        "Ajukan surat izin",
    ).json()

    conversation_id = str(
        first_payload["conversation_id"]
    )

    post_message(
        harness.client,
        "Siswa Batal",
        conversation_id=conversation_id,
    )

    cancel_response = post_message(
        harness.client,
        "batal",
        conversation_id=conversation_id,
    )

    assert cancel_response.status_code == 200

    cancel_payload = cancel_response.json()

    assert (
        cancel_payload["status"]
        == "answered"
    )

    assert cancel_payload["data"] is None

    with Session(
        harness.chatbot_engine
    ) as session:
        draft = session.get(
            PermissionDraft,
            conversation_id,
        )

        messages = list(
            session.scalars(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id
                    == conversation_id
                )
            )
        )

    assert draft is None

    assert all(
        message.storage_policy
        == "metadata_only"
        for message in messages
    )

    with Session(
        harness.academic_engine
    ) as session:
        request_count = session.scalar(
            select(func.count())
            .select_from(PermissionRequest)
        )

    assert request_count == 0


def test_regular_chat_does_not_force_metadata_only(
    harness: PermissionChatHarness,
) -> None:
    response = post_message(
        harness.client,
        "Siapa kepala sekolah?",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "unsupported"

    conversation_id = str(
        payload["conversation_id"]
    )

    with Session(
        harness.chatbot_engine
    ) as session:
        messages = list(
            session.scalars(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id
                    == conversation_id
                )
            )
        )

    assert len(messages) == 2

    assert all(
        message.storage_policy == "full"
        for message in messages
    )


def test_permission_source_key_is_idempotent(
    harness: PermissionChatHarness,
) -> None:
    source_key = (
        "chat:permission:"
        "00000000-0000-4000-8000-000000000001"
    )

    with Session(
        harness.academic_engine
    ) as session:
        repository = (
            PermissionRequestRepository(
                session
            )
        )

        first = submit_permission_request(
            student_name="Siswa Idempoten",
            class_name="7A",
            permission_type="sakit",
            description=(
                "Data sintetis untuk pengujian."
            ),
            phone_number=None,
            repository=repository,
            source_key=source_key,
        )

        second = submit_permission_request(
            student_name="Siswa Idempoten",
            class_name="7A",
            permission_type="sakit",
            description=(
                "Data sintetis untuk pengujian."
            ),
            phone_number=None,
            repository=repository,
            source_key=source_key,
        )

        assert first.status == "created"
        assert second.status == "created"

        assert first.request is not None
        assert second.request is not None

        assert (
            first.request.id
            == second.request.id
        )

        assert (
            first.request.tracking_code
            == second.request.tracking_code
        )

        request_count = session.scalar(
            select(func.count())
            .select_from(PermissionRequest)
            .where(
                PermissionRequest.source_key
                == source_key
            )
        )

        assert request_count == 1