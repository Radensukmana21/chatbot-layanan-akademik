from __future__ import annotations

from collections.abc import Generator
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_academic_session
from app.main import app
from app.models import (
    Base,
    Extracurricular,
    ExtracurricularSchedule,
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
        advisor = Teacher(
            name="Guru Pembina",
            normalized_name="guru pembina",
            is_active=True,
        )

        session.add(advisor)
        session.flush()

        pramuka = Extracurricular(
            name="Pramuka",
            normalized_name="pramuka",
            advisor_teacher_id=advisor.id,
            location="Lapangan",
            description="Kegiatan kepanduan",
            is_active=True,
            source_key="test:extracurricular:1",
        )

        pmr = Extracurricular(
            name="PMR",
            normalized_name="pmr",
            advisor_teacher_id=advisor.id,
            location="UKS",
            description="Palang Merah Remaja",
            is_active=True,
            source_key="test:extracurricular:2",
        )

        inactive_activity = Extracurricular(
            name="Kegiatan Tidak Aktif",
            normalized_name="kegiatan tidak aktif",
            advisor_teacher_id=advisor.id,
            location="Aula",
            description=None,
            is_active=False,
            source_key="test:extracurricular:3",
        )

        session.add_all([
            pramuka,
            pmr,
            inactive_activity,
        ])
        session.flush()

        session.add_all([
            ExtracurricularSchedule(
                extracurricular_id=pramuka.id,
                day="jumat",
                start_time=time(14, 0),
                end_time=time(16, 0),
                is_active=True,
                source_key=(
                    "test:extracurricular_schedule:1"
                ),
            ),
            ExtracurricularSchedule(
                extracurricular_id=pmr.id,
                day="rabu",
                start_time=time(14, 0),
                end_time=time(16, 0),
                is_active=True,
                source_key=(
                    "test:extracurricular_schedule:2"
                ),
            ),
            ExtracurricularSchedule(
                extracurricular_id=pramuka.id,
                day="senin",
                start_time=time(10, 0),
                end_time=time(11, 0),
                is_active=False,
                source_key=(
                    "test:extracurricular_schedule:3"
                ),
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


def test_lists_active_extracurriculars(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/extracurriculars"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["query"] is None
    assert len(payload["items"]) == 2

    names = [
        item["name"]
        for item in payload["items"]
    ]

    assert names == ["PMR", "Pramuka"]


def test_searches_extracurricular_by_name(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/extracurriculars/search",
        params={
            "q": "Pramuka",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["query"] == "pramuka"
    assert len(payload["items"]) == 1

    activity = payload["items"][0]

    assert activity["name"] == "Pramuka"
    assert activity["advisor_name"] == "Guru Pembina"
    assert activity["location"] == "Lapangan"
    assert activity["description"] == (
        "Kegiatan kepanduan"
    )

    assert activity["schedules"] == [
        {
            "day": "jumat",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        }
    ]


def test_excludes_inactive_extracurricular(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/extracurriculars/search",
        params={
            "q": "Kegiatan Tidak Aktif",
        },
    )

    assert response.status_code == 404


def test_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/extracurriculars/search",
        params={
            "q": "Tidak Ada",
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
        "/api/v1/extracurriculars/search",
        params={
            "q": "A",
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_query"
    )