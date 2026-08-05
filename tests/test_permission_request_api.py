from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.dependencies import (
    get_academic_session,
)
from app.main import app
from app.models import (
    AcademicYear,
    Base,
    SchoolClass,
)


@pytest.fixture
def client() -> Generator[
    TestClient,
    None,
    None,
]:
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


def valid_payload() -> dict[str, str]:
    return {
        "student_name": "Siswa Contoh",
        "class_name": "7A",
        "permission_type": "Sakit",
        "description": (
            "Tidak dapat mengikuti pelajaran."
        ),
        "phone_number": "081234000000",
    }


def test_creates_permission_request(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/permission-requests",
        json=valid_payload(),
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["tracking_code"].startswith(
        "IZN-"
    )
    assert payload["status"] == "pending"
    assert payload["submitted_at"] is not None

    assert "student_name" not in payload
    assert "class_name" not in payload
    assert "description" not in payload
    assert "phone_number" not in payload


def test_checks_permission_status(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/v1/permission-requests",
        json=valid_payload(),
    )

    tracking_code = (
        create_response.json()["tracking_code"]
    )

    response = client.get(
        "/api/v1/permission-requests/"
        f"{tracking_code}/status"
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["tracking_code"]
        == tracking_code
    )
    assert payload["status"] == "pending"
    assert payload["reviewed_at"] is None

    assert "student_name" not in payload
    assert "phone_number" not in payload


def test_accepts_lowercase_tracking_code(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/v1/permission-requests",
        json=valid_payload(),
    )

    tracking_code = (
        create_response
        .json()["tracking_code"]
        .lower()
    )

    response = client.get(
        "/api/v1/permission-requests/"
        f"{tracking_code}/status"
    )

    assert response.status_code == 200


def test_rejects_unknown_class(
    client: TestClient,
) -> None:
    payload = valid_payload()
    payload["class_name"] = "8A"

    response = client.post(
        "/api/v1/permission-requests",
        json=payload,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_class"
    )


def test_rejects_invalid_permission_type(
    client: TestClient,
) -> None:
    payload = valid_payload()
    payload["permission_type"] = "Liburan"

    response = client.post(
        "/api/v1/permission-requests",
        json=payload,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_permission_type"
    )


def test_rejects_invalid_phone_number(
    client: TestClient,
) -> None:
    payload = valid_payload()
    payload["phone_number"] = "nomor-salah"

    response = client.post(
        "/api/v1/permission-requests",
        json=payload,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_phone_number"
    )


def test_rejects_invalid_tracking_code(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/permission-requests/"
        "kode-salah/status"
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]["code"]
        == "invalid_code"
    )


def test_returns_not_found_for_unknown_code(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/permission-requests/"
        "IZN-000000000000/status"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]["code"]
        == "not_found"
    )