from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.repositories.school_class_repository import (
    MultipleActiveAcademicYearsError,
    SchoolClassRepository,
)
from app.services.class_validator import validate_class_format


ClassAvailabilityStatus = Literal[
    "active",
    "missing_class",
    "missing_group",
    "invalid_class_format",
    "not_registered",
    "no_active_academic_year",
    "configuration_error",
]


@dataclass(frozen=True, slots=True)
class ClassAvailabilityResult:
    status: ClassAvailabilityStatus
    class_name: str | None
    academic_year: str | None
    is_available: bool
    message: str


def check_class_availability(
    value: str | None,
    repository: SchoolClassRepository,
) -> ClassAvailabilityResult:
    """
    Memeriksa format kelas dan keberadaannya pada tahun ajaran aktif.
    """

    validation = validate_class_format(value)

    if not validation.is_valid:
        status = validation.error_code or "invalid_class_format"

        return ClassAvailabilityResult(
            status=status,  # type: ignore[arg-type]
            class_name=validation.class_name,
            academic_year=None,
            is_available=False,
            message=validation.message or "Nama kelas tidak valid.",
        )

    try:
        academic_year = repository.get_active_academic_year()
    except MultipleActiveAcademicYearsError:
        return ClassAvailabilityResult(
            status="configuration_error",
            class_name=validation.class_name,
            academic_year=None,
            is_available=False,
            message=(
                "Konfigurasi tahun ajaran sedang bermasalah. "
                "Silakan hubungi administrator sekolah."
            ),
        )

    if academic_year is None:
        return ClassAvailabilityResult(
            status="no_active_academic_year",
            class_name=validation.class_name,
            academic_year=None,
            is_available=False,
            message=(
                "Tahun ajaran aktif belum dikonfigurasi. "
                "Silakan hubungi administrator sekolah."
            ),
        )

    school_class = repository.find_active_class(
        academic_year_id=academic_year.id,
        class_name=validation.class_name,
    )

    if school_class is None:
        return ClassAvailabilityResult(
            status="not_registered",
            class_name=validation.class_name,
            academic_year=academic_year.name,
            is_available=False,
            message=(
                f"Format kelas {validation.class_name} valid, tetapi kelas "
                f"tersebut tidak terdaftar pada tahun ajaran "
                f"{academic_year.name}."
            ),
        )

    return ClassAvailabilityResult(
        status="active",
        class_name=school_class.class_name,
        academic_year=academic_year.name,
        is_available=True,
        message=(
            f"Kelas {school_class.class_name} aktif pada tahun ajaran "
            f"{academic_year.name}."
        ),
    )