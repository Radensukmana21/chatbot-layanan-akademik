from __future__ import annotations

from datetime import date, time
from collections.abc import Generator

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
                source_key="test:schedule:1",
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


def test_get_class_schedule(client: TestClient) -> None:
    response = client.get(
        "/api/v1/classes/7a/schedules/Senin"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["academic_year"] == "2025/2026"
    assert payload["class_name"] == "7A"
    assert payload["day"] == "senin"
    assert len(payload["items"]) == 1

    item = payload["items"][0]

    assert item["subject_name"] == "Matematika"
    assert item["teacher_name"] == "Guru Matematika"
    assert item["start_time"] == "07:00:00"
    assert item["end_time"] == "08:00:00"


def test_rejects_unknown_day(client: TestClient) -> None:
    response = client.get(
        "/api/v1/classes/7A/schedules/liburan"
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_day"


def test_rejects_unregistered_class(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/classes/8A/schedules/senin"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]["code"]
        == "class_not_registered"
    )


def test_returns_empty_schedule_for_valid_day(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/classes/7A/schedules/selasa"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []