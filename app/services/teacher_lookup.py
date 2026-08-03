from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.nlp.normalizers import normalize_text
from app.repositories.school_class_repository import (
    MultipleActiveAcademicYearsError,
    SchoolClassRepository,
)
from app.repositories.teacher_repository import (
    TeacherRepository,
)


TeacherSearchMode = Literal[
    "name",
    "subject",
]

TeacherLookupStatus = Literal[
    "ok",
    "invalid_query",
    "not_found",
    "no_active_academic_year",
    "configuration_error",
]


@dataclass(frozen=True, slots=True)
class TeacherInformation:
    id: int
    name: str
    subjects: tuple[str, ...]
    classes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TeacherLookupResult:
    status: TeacherLookupStatus
    search_mode: TeacherSearchMode
    query: str
    academic_year: str | None
    items: tuple[TeacherInformation, ...]
    message: str


TEACHER_HONORIFICS = {
    "pak",
    "bapak",
    "bu",
    "ibu",
    "guru",
}


def normalize_teacher_name_query(
    value: str,
) -> str:
    normalized = normalize_text(value)
    tokens = normalized.split()

    while (
        tokens
        and tokens[0] in TEACHER_HONORIFICS
    ):
        tokens.pop(0)

    return " ".join(tokens)


def normalize_subject_query(
    value: str,
) -> str:
    normalized = normalize_text(value)

    normalized = re.sub(
        r"^(?:mata\s+pelajaran|mapel|pelajaran)\s+",
        "",
        normalized,
    )

    return normalized.strip()


def lookup_teacher_information(
    *,
    query: str,
    search_mode: TeacherSearchMode,
    class_repository: SchoolClassRepository,
    teacher_repository: TeacherRepository,
) -> TeacherLookupResult:
    if search_mode == "name":
        normalized_query = normalize_teacher_name_query(
            query
        )
    else:
        normalized_query = normalize_subject_query(
            query
        )

    if len(normalized_query) < 2:
        return TeacherLookupResult(
            status="invalid_query",
            search_mode=search_mode,
            query=normalized_query,
            academic_year=None,
            items=(),
            message=(
                "Kata pencarian guru minimal "
                "terdiri dari dua karakter."
            ),
        )

    try:
        academic_year = (
            class_repository.get_active_academic_year()
        )
    except MultipleActiveAcademicYearsError:
        return TeacherLookupResult(
            status="configuration_error",
            search_mode=search_mode,
            query=normalized_query,
            academic_year=None,
            items=(),
            message=(
                "Terdapat lebih dari satu "
                "tahun ajaran aktif."
            ),
        )

    if academic_year is None:
        return TeacherLookupResult(
            status="no_active_academic_year",
            search_mode=search_mode,
            query=normalized_query,
            academic_year=None,
            items=(),
            message=(
                "Tahun ajaran aktif belum dikonfigurasi."
            ),
        )

    if search_mode == "name":
        teachers = teacher_repository.search_by_name(
            normalized_query=normalized_query,
        )
    else:
        teachers = teacher_repository.search_by_subject(
            normalized_query=normalized_query,
            academic_year_id=academic_year.id,
        )

    if not teachers:
        return TeacherLookupResult(
            status="not_found",
            search_mode=search_mode,
            query=normalized_query,
            academic_year=academic_year.name,
            items=(),
            message="Data guru tidak ditemukan.",
        )

    items = tuple(
        TeacherInformation(
            id=teacher.id,
            name=teacher.name,
            subjects=tuple(
                teacher_repository.list_subject_names(
                    teacher_id=teacher.id,
                    academic_year_id=academic_year.id,
                )
            ),
            classes=tuple(
                teacher_repository.list_class_names(
                    teacher_id=teacher.id,
                    academic_year_id=academic_year.id,
                )
            ),
        )
        for teacher in teachers
    )

    if search_mode == "name":
        message = (
            f"Ditemukan {len(items)} guru "
            f"yang sesuai dengan nama {query!r}."
        )
    else:
        message = (
            f"Ditemukan {len(items)} guru "
            f"untuk mata pelajaran {query!r}."
        )

    return TeacherLookupResult(
        status="ok",
        search_mode=search_mode,
        query=normalized_query,
        academic_year=academic_year.name,
        items=items,
        message=message,
    )