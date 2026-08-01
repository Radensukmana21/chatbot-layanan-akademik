from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Literal

from app.nlp.entity_extractor import extract_schedule_entities
from app.nlp.normalizers import normalize_text
from app.repositories.lesson_schedule_repository import (
    LessonScheduleRecord,
    LessonScheduleRepository,
)
from app.repositories.school_class_repository import (
    SchoolClassRepository,
)
from app.services.class_validator import validate_class_format
from app.services.schedule_lookup import lookup_class_schedule


ChatIntent = Literal["jadwal_pelajaran"]

ChatStatus = Literal[
    "answered",
    "needs_clarification",
    "invalid_request",
    "not_found",
    "unavailable",
    "unsupported",
]


@dataclass(frozen=True, slots=True)
class ChatResult:
    intent: ChatIntent | None
    intent_source: Literal["rule"] | None
    status: ChatStatus
    class_name: str | None
    day: str | None
    missing_entities: tuple[str, ...]
    academic_year: str | None
    items: tuple[LessonScheduleRecord, ...]
    message: str


def detect_rule_intent(
    message: str | None,
) -> ChatIntent | None:
    """
    Rule transparan untuk use case jadwal pelajaran.

    Model machine learning belum digunakan pada tahap ini.
    """

    normalized = normalize_text(message)

    if not normalized:
        return None

    tokens = set(normalized.split())

    if "jadwal" in tokens:
        return "jadwal_pelajaran"

    if "pelajaran" in tokens or "mapel" in tokens:
        return "jadwal_pelajaran"

    if re.search(r"\bbelajar\s+apa\b", normalized):
        return "jadwal_pelajaran"

    return None


def build_clarification_message(
    *,
    class_name: str | None,
    missing_entities: tuple[str, ...],
) -> str:
    missing = set(missing_entities)

    if missing == {"class_name", "day"}:
        return "Jadwal untuk kelas dan hari apa?"

    if missing == {"class_group", "day"}:
        return (
            f"Kelas {class_name} rombel apa, dan jadwal "
            "untuk hari apa?"
        )

    if "class_name" in missing:
        return "Jadwal untuk kelas berapa?"

    if "class_group" in missing:
        return (
            f"Kelas {class_name} rombel apa? "
            f"Contohnya {class_name}A."
        )

    return "Jadwal untuk hari apa?"


def handle_chat_message(
    *,
    message: str,
    class_repository: SchoolClassRepository,
    schedule_repository: LessonScheduleRepository,
    today: date | None = None,
) -> ChatResult:
    normalized_message = normalize_text(message)

    if not normalized_message:
        return ChatResult(
            intent=None,
            intent_source=None,
            status="invalid_request",
            class_name=None,
            day=None,
            missing_entities=(),
            academic_year=None,
            items=(),
            message="Pesan tidak boleh kosong.",
        )

    intent = detect_rule_intent(message)

    if intent is None:
        return ChatResult(
            intent=None,
            intent_source=None,
            status="unsupported",
            class_name=None,
            day=None,
            missing_entities=(),
            academic_year=None,
            items=(),
            message=(
                "Maaf, saat ini saya baru dapat membantu "
                "mengecek jadwal pelajaran."
            ),
        )

    entities = extract_schedule_entities(
        message,
        today=today,
    )

    missing_entities: list[str] = []

    if entities.class_name is None:
        missing_entities.append("class_name")
    else:
        class_validation = validate_class_format(
            entities.class_name
        )

        if class_validation.error_code == "missing_group":
            missing_entities.append("class_group")
        elif not class_validation.is_valid:
            return ChatResult(
                intent=intent,
                intent_source="rule",
                status="invalid_request",
                class_name=class_validation.class_name,
                day=entities.day,
                missing_entities=(),
                academic_year=None,
                items=(),
                message=(
                    class_validation.message
                    or "Format kelas tidak valid."
                ),
            )

    if entities.day is None:
        missing_entities.append("day")

    if missing_entities:
        missing_tuple = tuple(missing_entities)

        return ChatResult(
            intent=intent,
            intent_source="rule",
            status="needs_clarification",
            class_name=entities.class_name,
            day=entities.day,
            missing_entities=missing_tuple,
            academic_year=None,
            items=(),
            message=build_clarification_message(
                class_name=entities.class_name,
                missing_entities=missing_tuple,
            ),
        )

    assert entities.class_name is not None
    assert entities.day is not None

    lookup = lookup_class_schedule(
        class_name=entities.class_name,
        day=entities.day,
        class_repository=class_repository,
        schedule_repository=schedule_repository,
    )

    if lookup.status == "class_not_registered":
        return ChatResult(
            intent=intent,
            intent_source="rule",
            status="not_found",
            class_name=lookup.class_name,
            day=lookup.day,
            missing_entities=(),
            academic_year=lookup.academic_year,
            items=(),
            message=lookup.message,
        )

    if lookup.status in {
        "no_active_academic_year",
        "configuration_error",
    }:
        return ChatResult(
            intent=intent,
            intent_source="rule",
            status="unavailable",
            class_name=lookup.class_name,
            day=lookup.day,
            missing_entities=(),
            academic_year=lookup.academic_year,
            items=(),
            message=(
                "Data jadwal sedang tidak tersedia. "
                "Silakan hubungi administrator sekolah."
            ),
        )

    if lookup.status != "ok":
        return ChatResult(
            intent=intent,
            intent_source="rule",
            status="invalid_request",
            class_name=lookup.class_name,
            day=lookup.day,
            missing_entities=(),
            academic_year=lookup.academic_year,
            items=(),
            message=lookup.message,
        )

    if lookup.items:
        response_message = (
            f"Berikut jadwal kelas {lookup.class_name} "
            f"pada hari {lookup.day.title()}."
        )
    else:
        response_message = lookup.message

    return ChatResult(
        intent=intent,
        intent_source="rule",
        status="answered",
        class_name=lookup.class_name,
        day=lookup.day,
        missing_entities=(),
        academic_year=lookup.academic_year,
        items=lookup.items,
        message=response_message,
    )