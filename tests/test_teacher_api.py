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
        connect_args={
            "check_same_thread": False,
        },
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

        class_7a = SchoolClass(
            academic_year_id=academic_year.id,
            class_name="7A",
            grade=7,
            group_letter="A",
            is_active=True,
        )

        class_8a = SchoolClass(
            academic_year_id=academic_year.id,
            class_name="8A",
            grade=8,
            group_letter="A",
            is_active=True,
        )

        session.add_all([
            class_7a,
            class_8a,
        ])

        mathematics = Subject(
            name="Matematika",
            normalized_name="matematika",
            subject_type="lesson",
            is_active=True,
        )

        indonesian = Subject(
            name="Bahasa Indonesia",
            normalized_name="bahasa indonesia",
            subject_type="lesson",
            is_active=True,
        )

        session.add_all([
            mathematics,
            indonesian,
        ])

        teacher_ane = Teacher(
            name="Hj. Ane Rostiana, S.Pd",
            normalized_name=(
                "hj ane rostiana s pd"
            ),
            is_active=True,
        )

        teacher_windy = Teacher(
            name="Windy Tantriyani, S.Pd",
            normalized_name=(
                "windy tantriyani s pd"
            ),
            is_active=True,
        )

        session.add_all([
            teacher_ane,
            teacher_windy,
        ])
        session.flush()

        session.add_all([
            LessonSchedule(
                school_class_id=class_7a.id,
                subject_id=mathematics.id,
                teacher_id=teacher_ane.id,
                day="senin",
                start_time=time(7, 0),
                end_time=time(8, 0),
                is_active=True,
                source_key="test:teacher:1",
            ),
            LessonSchedule(
                school_class_id=class_8a.id,
                subject_id=mathematics.id,
                teacher_id=teacher_ane.id,
                day="selasa",
                start_time=time(7, 0),
                end_time=time(8, 0),
                is_active=True,
                source_key="test:teacher:2",
            ),
            LessonSchedule(
                school_class_id=class_7a.id,
                subject_id=indonesian.id,
                teacher_id=teacher_windy.id,
                day="rabu",
                start_time=time(8, 0),
                end_time=time(9, 0),
                is_active=True,
                source_key="test:teacher:3",
            ),
        ])

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

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_searches_teacher_by_name(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/teachers/search",
        params={
            "q": "Ibu Ane",
            "by": "name",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["search_mode"] == "name"
    assert payload["academic_year"] == "2025/2026"
    assert len(payload["items"]) == 1

    teacher = payload["items"][0]

    assert teacher["name"] == "Hj. Ane Rostiana, S.Pd"
    assert teacher["subjects"] == ["Matematika"]
    assert teacher["classes"] == ["7A", "8A"]


def test_searches_teachers_by_subject(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/teachers/search",
        params={
            "q": "Matematika",
            "by": "subject",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["search_mode"] == "subject"
    assert len(payload["items"]) == 1
    assert (
        payload["items"][0]["name"]
        == "Hj. Ane Rostiana, S.Pd"
    )


def test_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/teachers/search",
        params={
            "q": "Guru Tidak Ada",
            "by": "name",
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]["code"]
        == "not_found"
    )


def test_rejects_short_query(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/teachers/search",
        params={
            "q": "A",
            "by": "name",
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_query"
    )