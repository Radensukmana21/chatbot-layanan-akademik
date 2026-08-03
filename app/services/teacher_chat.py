from __future__ import annotations

from dataclasses import dataclass
import re

from app.nlp.normalizers import normalize_text
from app.services.teacher_lookup import (
    TeacherInformation,
    TeacherSearchMode,
)


@dataclass(frozen=True, slots=True)
class TeacherChatQuery:
    is_teacher_intent: bool
    search_mode: TeacherSearchMode | None
    query: str | None


NAME_PATTERNS = (
    re.compile(
        r"^(?:pak|bapak|bu|ibu|guru)\s+"
        r"(?P<query>.+?)\s+"
        r"(?:mengajar|ngajar)(?:\s+apa)?$"
    ),
    re.compile(
        r"^(?:apa|mapel apa|pelajaran apa)\s+yang\s+"
        r"(?:diajarkan|diajar)\s+"
        r"(?:oleh\s+)?"
        r"(?:pak|bapak|bu|ibu|guru)\s+"
        r"(?P<query>.+)$"
    ),
    re.compile(
        r"^(?:info|informasi|data)\s+"
        r"(?:tentang\s+)?"
        r"(?:pak|bapak|bu|ibu)\s+"
        r"(?P<query>.+)$"
    ),
)

SUBJECT_PATTERNS = (
    re.compile(
        r"^siapa\s+(?:guru|pengajar)"
        r"(?:\s+(?:mapel|mata pelajaran|pelajaran))?"
        r"\s+(?P<query>.+)$"
    ),
    re.compile(
        r"^siapa\s+yang\s+"
        r"(?:mengajar|ngajar)\s+"
        r"(?P<query>.+)$"
    ),
    re.compile(
        r"^(?:guru|pengajar)\s+"
        r"(?P<query>.+?)\s+siapa$"
    ),
    re.compile(
        r"^(?:guru|pengajar)\s+"
        r"(?:mapel|mata pelajaran|pelajaran)\s+"
        r"(?P<query>.+)$"
    ),
)


def extract_teacher_chat_query(
    message: str | None,
) -> TeacherChatQuery:
    normalized = normalize_text(message)

    if not normalized:
        return TeacherChatQuery(
            is_teacher_intent=False,
            search_mode=None,
            query=None,
        )

    for pattern in NAME_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            return TeacherChatQuery(
                is_teacher_intent=True,
                search_mode="name",
                query=match.group("query").strip(),
            )

    for pattern in SUBJECT_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            return TeacherChatQuery(
                is_teacher_intent=True,
                search_mode="subject",
                query=match.group("query").strip(),
            )

    tokens = set(normalized.split())

    if tokens.intersection(
        {
            "guru",
            "pengajar",
            "mengajar",
            "ngajar",
        }
    ):
        return TeacherChatQuery(
            is_teacher_intent=True,
            search_mode=None,
            query=None,
        )

    return TeacherChatQuery(
        is_teacher_intent=False,
        search_mode=None,
        query=None,
    )


def build_teacher_answer(
    *,
    search_mode: TeacherSearchMode,
    query: str,
    items: tuple[TeacherInformation, ...],
) -> str:
    if search_mode == "name" and len(items) == 1:
        teacher = items[0]

        subjects = (
            ", ".join(teacher.subjects)
            if teacher.subjects
            else "belum memiliki data mata pelajaran"
        )

        classes = (
            ", ".join(teacher.classes)
            if teacher.classes
            else "belum memiliki data kelas"
        )

        return (
            f"{teacher.name} mengajar {subjects} "
            f"untuk kelas {classes}."
        )

    if search_mode == "subject":
        teacher_names = ", ".join(
            item.name
            for item in items
        )

        return (
            f"Guru untuk mata pelajaran {query} adalah "
            f"{teacher_names}."
        )

    return (
        f"Ditemukan {len(items)} guru yang sesuai "
        f"dengan pencarian {query!r}."
    )