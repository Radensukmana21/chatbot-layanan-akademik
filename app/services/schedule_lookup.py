from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.nlp.normalizers import DAY_ALIASES, normalize_text
from app.repositories.lesson_schedule_repository import (
    LessonScheduleRecord,
    LessonScheduleRepository,
)
from app.repositories.school_class_repository import (
    MultipleActiveAcademicYearsError,
    SchoolClassRepository,
)
from app.services.class_validator import validate_class_format


ScheduleLookupStatus = Literal[
    "ok",
    "invalid_class",
    "invalid_day",
    "class_not_registered",
    "no_active_academic_year",
    "configuration_error",
]


@dataclass(frozen=True, slots=True)
class ScheduleLookupResult:
    status: ScheduleLookupStatus
    class_name: str | None
    day: str | None
    academic_year: str | None
    items: tuple[LessonScheduleRecord, ...]
    message: str


def normalize_day(value: str) -> str | None:
    normalized = normalize_text(value)
    return DAY_ALIASES.get(normalized)


def lookup_class_schedule(
    *,
    class_name: str,
    day: str,
    class_repository: SchoolClassRepository,
    schedule_repository: LessonScheduleRepository,
) -> ScheduleLookupResult:
    class_validation = validate_class_format(class_name)

    if (
        not class_validation.is_valid
        or class_validation.class_name is None
    ):
        return ScheduleLookupResult(
            status="invalid_class",
            class_name=class_validation.class_name,
            day=None,
            academic_year=None,
            items=(),
            message=(
                class_validation.message
                or "Format kelas tidak valid."
            ),
        )

    normalized_day = normalize_day(day)

    if normalized_day is None:
        return ScheduleLookupResult(
            status="invalid_day",
            class_name=class_validation.class_name,
            day=None,
            academic_year=None,
            items=(),
            message=f"Nama hari {day!r} tidak dikenali.",
        )

    try:
        academic_year = (
            class_repository.get_active_academic_year()
        )
    except MultipleActiveAcademicYearsError:
        return ScheduleLookupResult(
            status="configuration_error",
            class_name=class_validation.class_name,
            day=normalized_day,
            academic_year=None,
            items=(),
            message=(
                "Terdapat lebih dari satu tahun ajaran aktif."
            ),
        )

    if academic_year is None:
        return ScheduleLookupResult(
            status="no_active_academic_year",
            class_name=class_validation.class_name,
            day=normalized_day,
            academic_year=None,
            items=(),
            message="Tahun ajaran aktif belum dikonfigurasi.",
        )

    school_class = class_repository.find_active_class(
        academic_year_id=academic_year.id,
        class_name=class_validation.class_name,
    )

    if school_class is None:
        return ScheduleLookupResult(
            status="class_not_registered",
            class_name=class_validation.class_name,
            day=normalized_day,
            academic_year=academic_year.name,
            items=(),
            message=(
                f"Kelas {class_validation.class_name} tidak "
                f"terdaftar pada tahun ajaran "
                f"{academic_year.name}."
            ),
        )

    items = schedule_repository.list_for_class_and_day(
        school_class_id=school_class.id,
        day=normalized_day,
    )

    if items:
        message = (
            f"Ditemukan {len(items)} jadwal untuk kelas "
            f"{school_class.class_name} pada hari "
            f"{normalized_day.title()}."
        )
    else:
        message = (
            f"Belum ada jadwal untuk kelas "
            f"{school_class.class_name} pada hari "
            f"{normalized_day.title()}."
        )

    return ScheduleLookupResult(
        status="ok",
        class_name=school_class.class_name,
        day=normalized_day,
        academic_year=academic_year.name,
        items=tuple(items),
        message=message,
    )