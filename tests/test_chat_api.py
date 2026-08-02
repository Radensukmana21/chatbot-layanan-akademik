from __future__ import annotations

from collections.abc import Generator
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_academic_session
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
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
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

    def override_session() -> Generator[
        Session,
        None,
        None,
    ]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[
        get_academic_session
    ] = override_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def post_message(
    client: TestClient,
    message: str,
    context: dict[str, object] | None = None,
):
    payload: dict[str, object] = {
        "message": message,
    }

    if context is not None:
        payload["context"] = context

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

    payload = response.json()

    assert response.status_code == 200
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

    payload = response.json()

    assert payload["status"] == "unsupported"
    assert payload["intent"] is None
    assert payload["intent_source"] is None


def test_rejects_whitespace_message(
    client: TestClient,
) -> None:
    response = post_message(client, "   ")

    payload = response.json()

    assert response.status_code == 200
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

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["context"] == {
        "intent": "jadwal_pelajaran",
        "class_name": None,
        "day": "senin",
        "is_active": True,
    }

    second_response = post_message(
        client,
        "7A",
        context=first_payload["context"],
    )

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["entities"] == {
        "class_name": "7A",
        "day": "senin",
    }
    assert second_payload["context"]["is_active"] is False
    assert len(second_payload["data"]["items"]) == 1

def test_continues_with_day_reply(
    client: TestClient,
) -> None:
    first_response = post_message(
        client,
        "Jadwal kelas 7A",
    )

    first_payload = first_response.json()

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == ["day"]

    second_response = post_message(
        client,
        "Senin",
        context=first_payload["context"],
    )

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["entities"]["class_name"] == "7A"
    assert second_payload["entities"]["day"] == "senin"

def test_continues_with_group_only_reply(
    client: TestClient,
) -> None:
    first_response = post_message(
        client,
        "Jadwal kelas 7 hari Senin",
    )

    first_payload = first_response.json()

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == ["class_group"]
    assert first_payload["context"]["class_name"] == "7"

    second_response = post_message(
        client,
        "A",
        context=first_payload["context"],
    )

    second_payload = second_response.json()

    assert second_payload["status"] == "answered"
    assert second_payload["entities"]["class_name"] == "7A"

def test_does_not_reuse_completed_context(
    client: TestClient,
) -> None:
    answered_response = post_message(
        client,
        "Jadwal kelas 7A hari Senin",
    )

    answered_payload = answered_response.json()

    assert answered_payload["status"] == "answered"
    assert answered_payload["context"]["is_active"] is False

    follow_up_response = post_message(
        client,
        "Terima kasih",
        context=answered_payload["context"],
    )

    follow_up_payload = follow_up_response.json()

    assert follow_up_payload["status"] == "unsupported"
    assert follow_up_payload["intent"] is None

def test_continues_schedule_in_four_turns(
    client: TestClient,
) -> None:
    first_response = post_message(
        client,
        "Jadwal",
    )
    first_payload = first_response.json()

    assert first_payload["status"] == "needs_clarification"
    assert first_payload["missing_entities"] == [
        "class_name",
        "day",
    ]

    second_response = post_message(
        client,
        "7",
        context=first_payload["context"],
    )
    second_payload = second_response.json()

    assert second_payload["status"] == "needs_clarification"
    assert second_payload["entities"] == {
        "class_name": "7",
        "day": None,
    }
    assert second_payload["missing_entities"] == [
        "class_group",
        "day",
    ]

    third_response = post_message(
        client,
        "A",
        context=second_payload["context"],
    )
    third_payload = third_response.json()

    assert third_payload["status"] == "needs_clarification"
    assert third_payload["entities"] == {
        "class_name": "7A",
        "day": None,
    }
    assert third_payload["missing_entities"] == ["day"]

    fourth_response = post_message(
        client,
        "Senin",
        context=third_payload["context"],
    )
    fourth_payload = fourth_response.json()

    assert fourth_payload["status"] == "answered"
    assert fourth_payload["entities"] == {
        "class_name": "7A",
        "day": "senin",
    }
    assert fourth_payload["context"]["is_active"] is False
    assert fourth_payload["data"] is not None