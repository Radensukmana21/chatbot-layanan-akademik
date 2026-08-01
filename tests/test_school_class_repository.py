from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AcademicYear, Base, SchoolClass
from app.repositories.school_class_repository import (
    MultipleActiveAcademicYearsError,
    SchoolClassRepository,
)
from app.services.class_availability import check_class_availability


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as database_session:
        yield database_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def create_academic_year(
    session: Session,
    *,
    name: str = "2026/2027",
    is_active: bool = True,
) -> AcademicYear:
    academic_year = AcademicYear(
        name=name,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_active=is_active,
    )

    session.add(academic_year)
    session.flush()

    return academic_year


def create_school_class(
    session: Session,
    *,
    academic_year: AcademicYear,
    class_name: str,
    is_active: bool = True,
) -> SchoolClass:
    school_class = SchoolClass(
        academic_year_id=academic_year.id,
        class_name=class_name,
        grade=int(class_name[0]),
        group_letter=class_name[1],
        is_active=is_active,
    )

    session.add(school_class)
    session.flush()

    return school_class


def test_returns_no_active_academic_year(
    session: Session,
) -> None:
    repository = SchoolClassRepository(session)

    assert repository.get_active_academic_year() is None


def test_returns_single_active_academic_year(
    session: Session,
) -> None:
    create_academic_year(session)

    repository = SchoolClassRepository(session)
    result = repository.get_active_academic_year()

    assert result is not None
    assert result.name == "2026/2027"


def test_rejects_multiple_active_academic_years(
    session: Session,
) -> None:
    create_academic_year(
        session,
        name="2025/2026",
    )

    second_year = AcademicYear(
        name="2026/2027",
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_active=True,
    )
    session.add(second_year)
    session.flush()

    repository = SchoolClassRepository(session)

    with pytest.raises(MultipleActiveAcademicYearsError):
        repository.get_active_academic_year()


def test_finds_active_class(
    session: Session,
) -> None:
    academic_year = create_academic_year(session)

    create_school_class(
        session,
        academic_year=academic_year,
        class_name="8J",
    )

    repository = SchoolClassRepository(session)

    result = repository.find_active_class(
        academic_year_id=academic_year.id,
        class_name="8J",
    )

    assert result is not None
    assert result.class_name == "8J"


def test_does_not_return_inactive_class(
    session: Session,
) -> None:
    academic_year = create_academic_year(session)

    create_school_class(
        session,
        academic_year=academic_year,
        class_name="8K",
        is_active=False,
    )

    repository = SchoolClassRepository(session)

    result = repository.find_active_class(
        academic_year_id=academic_year.id,
        class_name="8K",
    )

    assert result is None


def test_lists_active_classes_in_order(
    session: Session,
) -> None:
    academic_year = create_academic_year(session)

    create_school_class(
        session,
        academic_year=academic_year,
        class_name="9A",
    )
    create_school_class(
        session,
        academic_year=academic_year,
        class_name="7B",
    )
    create_school_class(
        session,
        academic_year=academic_year,
        class_name="7A",
    )
    create_school_class(
        session,
        academic_year=academic_year,
        class_name="8A",
        is_active=False,
    )

    repository = SchoolClassRepository(session)

    result = repository.list_active_class_names(
        academic_year_id=academic_year.id,
    )

    assert result == ["7A", "7B", "9A"]


def test_class_availability_accepts_registered_class(
    session: Session,
) -> None:
    academic_year = create_academic_year(session)

    create_school_class(
        session,
        academic_year=academic_year,
        class_name="8J",
    )

    repository = SchoolClassRepository(session)

    result = check_class_availability(
        "8J",
        repository,
    )

    assert result.status == "active"
    assert result.is_available is True
    assert result.class_name == "8J"
    assert result.academic_year == "2026/2027"


def test_class_availability_rejects_unregistered_class(
    session: Session,
) -> None:
    create_academic_year(session)

    repository = SchoolClassRepository(session)

    result = check_class_availability(
        "8K",
        repository,
    )

    assert result.status == "not_registered"
    assert result.is_available is False
    assert result.class_name == "8K"


def test_class_availability_rejects_invalid_format(
    session: Session,
) -> None:
    repository = SchoolClassRepository(session)

    result = check_class_availability(
        "8Z",
        repository,
    )

    assert result.status == "invalid_class_format"
    assert result.is_available is False


def test_class_availability_requires_group(
    session: Session,
) -> None:
    repository = SchoolClassRepository(session)

    result = check_class_availability(
        "8",
        repository,
    )

    assert result.status == "missing_group"
    assert result.is_available is False


def test_class_availability_handles_missing_active_year(
    session: Session,
) -> None:
    repository = SchoolClassRepository(session)

    result = check_class_availability(
        "8A",
        repository,
    )

    assert result.status == "no_active_academic_year"
    assert result.is_available is False