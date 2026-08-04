from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AcademicYear,
    Base,
    PermissionRequest,
    SchoolClass,
)


@pytest.fixture
def engine():
    database_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
    )

    Base.metadata.create_all(database_engine)

    try:
        yield database_engine
    finally:
        Base.metadata.drop_all(database_engine)
        database_engine.dispose()


def create_school_class(
    session: Session,
) -> SchoolClass:
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
    session.flush()

    return school_class


def test_creates_permission_request(
    engine,
) -> None:
    with Session(engine) as session:
        school_class = create_school_class(session)

        request = PermissionRequest(
            tracking_code="IZN-TEST-0001",
            school_class_id=school_class.id,
            class_name="7A",
            student_name="Siswa Contoh",
            permission_type="sakit",
            description="Tidak dapat mengikuti kegiatan.",
            phone_number="081234000000",
            status="pending",
        )

        session.add(request)
        session.commit()

    with Session(engine) as session:
        stored = session.scalar(
            select(PermissionRequest).where(
                PermissionRequest.tracking_code
                == "IZN-TEST-0001"
            )
        )

        assert stored is not None
        assert stored.class_name == "7A"
        assert stored.permission_type == "sakit"
        assert stored.status == "pending"
        assert stored.school_class_id is not None
        assert stored.submitted_at is not None


def test_tracking_code_must_be_unique(
    engine,
) -> None:
    with Session(engine) as session:
        school_class = create_school_class(session)

        session.add_all([
            PermissionRequest(
                tracking_code="IZN-DUPLICATE",
                school_class_id=school_class.id,
                class_name="7A",
                student_name="Siswa Pertama",
                permission_type="sakit",
                status="pending",
            ),
            PermissionRequest(
                tracking_code="IZN-DUPLICATE",
                school_class_id=school_class.id,
                class_name="7A",
                student_name="Siswa Kedua",
                permission_type="keperluan",
                status="pending",
            ),
        ])

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_phone_number_can_be_null(
    engine,
) -> None:
    with Session(engine) as session:
        school_class = create_school_class(session)

        request = PermissionRequest(
            tracking_code="IZN-TEST-NULL-PHONE",
            school_class_id=school_class.id,
            class_name="7A",
            student_name="Siswa Contoh",
            permission_type="keperluan",
            description=None,
            phone_number=None,
            status="pending",
        )

        session.add(request)
        session.commit()

        assert request.id is not None