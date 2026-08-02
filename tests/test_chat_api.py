from __future__ import annotations

from collections.abc import Generator
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.chatbot_models import ChatbotBase
from app.core.dependencies import (
    get_academic_session,
    get_chatbot_session,
)
from app.main import app
from app.models import (
    AcademicYear,
    Base,
    LessonSchedule,
    SchoolClass,
    Subject,
    Teacher,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    academic_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    chatbot_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(academic_engine)
    ChatbotBase.metadata.create_all(chatbot_engine)

    with Session(academic_engine) as session:
        academic_year = AcademicYear(
            name="2025/2026",
            start_date=date(2025, 7, 1),
            end_date=date(2026, 6, 30),
            is_active=True,
        )
        session.add(academic_year)
        session.flush()

        school_class = SchoolClass(
            academic_year_id=academic_year.id,
            class_name="7A",
            grade=7,
            group_letter="A",
            is_active=True,
        )
        session.add(school_class)

        subject = Subject(
            name="Matematika",
            normalized_name="matematika",
            subject_type="lesson",
            is_active=True,
        )
        session.add(subject)

        teacher = Teacher(
            name="Guru Matematika",
            normalized_name="guru matematika",
            is_active=True,
        )
        session.add(teacher)
        session.flush()

        session.add(
            LessonSchedule(
                school_class_id=school_class.id,
                subject_id=subject.id,
                teacher_id=teacher.id,
                day="senin",
                start_time=time(7, 0),
                end_time=time(8, 0),
                is_active=True,
                source_key="test:chat:schedule:1",
            )
        )

        session.commit()

    def override_academic_session() -> Generator[
        Session,
        None,
        None,
    ]:
        with Session(academic_engine) as session:
            yield session

    def override_chatbot_session() -> Generator[
        Session,
        None,
        None,
    ]:
        with Session(chatbot_engine) as session:
            yield session

    app.dependency_overrides[
        get_academic_session
    ] = override_academic_session

    app.dependency_overrides[
        get_chatbot_session
    ] = override_chatbot_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

        Base.metadata.drop_all(academic_engine)
        ChatbotBase.metadata.drop_all(chatbot_engine)

        academic_engine.dispose()
        chatbot_engine.dispose()


def post_message(
    client: TestClient,
    message: str,
    conversation_id: str | None = None,
):
    payload: dict[str, object] = {
        "message": message,
    }

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    return client.post(
        "/api/v1/chat/messages",
        json=payload,
    )


def test_answers_schedule_request(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal kelas 7A hari Senin",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["conversation_id"] is not None
    assert payload["intent"] == "jadwal_pelajaran"
    assert payload["intent_source"] == "rule"
    assert payload["status"] == "answered"

    assert payload["entities"] == {
        "class_name": "7A",
        "day": "senin",
    }

    assert payload["missing_entities"] == []
    assert payload["data"]["academic_year"] == "2025/2026"
    assert len(payload["data"]["items"]) == 1

    item = payload["data"]["items"][0]

    assert item["subject_name"] == "Matematika"
    assert item["teacher_name"] == "Guru Matematika"


def test_requests_missing_class(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal hari Senin",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["conversation_id"] is not None
    assert payload["status"] == "needs_clarification"
    assert payload["missing_entities"] == ["class_name"]
    assert payload["entities"]["day"] == "senin"
    assert payload["data"] is None


def test_requests_missing_day(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal kelas 7A",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "needs_clarification"
    assert payload["missing_entities"] == ["day"]
    assert payload["entities"]["class_name"] == "7A"


def test_requests_missing_class_group(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal kelas 8 hari Senin",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "needs_clarification"
    assert payload["missing_entities"] == ["class_group"]
    assert payload["entities"]["class_name"] == "8"


def test_rejects_invalid_class_format(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal kelas 8Z hari Senin",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "invalid_request"
    assert payload["entities"]["class_name"] == "8Z"
    assert payload["data"] is None


def test_returns_not_found_for_inactive_class(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Jadwal kelas 8A hari Senin",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "not_found"
    assert payload["intent"] == "jadwal_pelajaran"
    assert payload["data"] is None


def test_returns_unsupported_for_other_intent(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "Siapa kepala sekolah?",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "unsupported"
    assert payload["intent"] is None
    assert payload["intent_source"] is None


def test_rejects_whitespace_message(
    client: TestClient,
) -> None:
    response = post_message(client, "   ")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "invalid_request"
    assert payload["message"] == "Pesan tidak boleh kosong."


def test_continues_with_class_reply(
    client: TestClient,
) -> None:
    first_response = post_message(
        client,
        "Jadwal hari Senin",
    )

    first_payload = first_response.json()
    conversation_id = first_payload["conversation_id"]

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["entities"] == {
        "class_name": None,
        "day": "senin",
    }

    second_response = post_message(
        client,
        "7A",
        conversation_id=conversation_id,
    )

    assert second_response.status_code == 200

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["conversation_id"] == conversation_id
    assert second_payload["entities"] == {
        "class_name": "7A",
        "day": "senin",
    }
    assert len(second_payload["data"]["items"]) == 1


def test_continues_with_day_reply(
    client: TestClient,
) -> None:
    first_payload = post_message(
        client,
        "Jadwal kelas 7A",
    ).json()

    conversation_id = first_payload["conversation_id"]

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == ["day"]

    second_response = post_message(
        client,
        "Senin",
        conversation_id=conversation_id,
    )

    assert second_response.status_code == 200

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["conversation_id"] == conversation_id
    assert second_payload["entities"]["class_name"] == "7A"
    assert second_payload["entities"]["day"] == "senin"


def test_continues_with_group_only_reply(
    client: TestClient,
) -> None:
    first_payload = post_message(
        client,
        "Jadwal kelas 7 hari Senin",
    ).json()

    conversation_id = first_payload["conversation_id"]

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == ["class_group"]
    assert first_payload["entities"]["class_name"] == "7"

    second_response = post_message(
        client,
        "A",
        conversation_id=conversation_id,
    )

    assert second_response.status_code == 200

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["conversation_id"] == conversation_id
    assert second_payload["entities"]["class_name"] == "7A"


def test_does_not_reuse_completed_conversation(
    client: TestClient,
) -> None:
    answered_payload = post_message(
        client,
        "Jadwal kelas 7A hari Senin",
    ).json()

    conversation_id = answered_payload["conversation_id"]

    follow_up_response = post_message(
        client,
        "Terima kasih",
        conversation_id=conversation_id,
    )

    assert follow_up_response.status_code == 200

    follow_up_payload = follow_up_response.json()

    assert follow_up_payload["status"] == "unsupported"
    assert follow_up_payload["intent"] is None
    assert follow_up_payload["conversation_id"] == conversation_id


def test_continues_schedule_in_four_turns(
    client: TestClient,
) -> None:
    first_payload = post_message(
        client,
        "Jadwal",
    ).json()

    conversation_id = first_payload["conversation_id"]

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == [
        "class_name",
        "day",
    ]

    second_payload = post_message(
        client,
        "7",
        conversation_id=conversation_id,
    ).json()

    assert second_payload["status"] == "needs_clarification"
    assert second_payload["conversation_id"] == conversation_id
    assert second_payload["entities"] == {
        "class_name": "7",
        "day": None,
    }
    assert second_payload["missing_entities"] == [
        "class_group",
        "day",
    ]

    third_payload = post_message(
        client,
        "A",
        conversation_id=conversation_id,
    ).json()

    assert third_payload["status"] == "needs_clarification"
    assert third_payload["conversation_id"] == conversation_id
    assert third_payload["entities"] == {
        "class_name": "7A",
        "day": None,
    }
    assert third_payload["missing_entities"] == ["day"]

    fourth_payload = post_message(
        client,
        "Senin",
        conversation_id=conversation_id,
    ).json()

    assert fourth_payload["status"] == "answered"
    assert fourth_payload["conversation_id"] == conversation_id
    assert fourth_payload["entities"] == {
        "class_name": "7A",
        "day": "senin",
    }
    assert fourth_payload["data"] is not None


def test_rejects_unknown_conversation_id(
    client: TestClient,
) -> None:
    response = post_message(
        client,
        "7A",
        conversation_id=(
            "00000000-0000-4000-8000-000000000000"
        ),
    )

    assert response.status_code == 404

    payload = response.json()

    assert (
        payload["detail"]["code"]
        == "conversation_not_found"
    )