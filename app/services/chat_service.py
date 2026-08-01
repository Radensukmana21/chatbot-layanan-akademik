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
class ChatContext:
    intent: ChatIntent | None = None
    class_name: str | None = None
    day: str | None = None
    is_active: bool = False


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
    context: ChatContext


def detect_rule_intent(
    message: str | None,
) -> ChatIntent | None:
    """
    Mendeteksi intent jadwal menggunakan rule transparan.

    Machine learning belum digunakan pada tahap ini.
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


def extract_group_reply(
    message: str | None,
) -> str | None:
    """
    Mengambil jawaban rombel pendek.

    Contoh yang diterima:
    - A
    - rombel A
    - grup B
    - kelas C
    """

    normalized = normalize_text(message)

    match = re.fullmatch(
        r"(?:rombel|grup|kelas)?\s*([a-k])",
        normalized,
    )

    if match is None:
        return None

    return match.group(1).upper()


def merge_schedule_context(
    *,
    message: str,
    previous_context: ChatContext,
    today: date | None = None,
) -> ChatContext:
    """
    Menggabungkan entitas dari pesan baru dengan percakapan aktif.

    Entitas pada pesan baru mempunyai prioritas lebih tinggi.
    """

    extracted = extract_schedule_entities(
        message,
        today=today,
    )

    use_previous_context = (
        previous_context.is_active
        and previous_context.intent == "jadwal_pelajaran"
    )

    previous_class = (
        previous_context.class_name
        if use_previous_context
        else None
    )

    previous_day = (
        previous_context.day
        if use_previous_context
        else None
    )

    class_name = extracted.class_name or previous_class
    day = extracted.day or previous_day

    # Jika sebelumnya pengguna hanya menyebut "kelas 7",
    # jawaban pendek "A" diubah menjadi "7A".
    if (
        extracted.class_name is None
        and previous_class is not None
        and re.fullmatch(r"[789]", previous_class)
    ):
        group = extract_group_reply(message)

        if group is not None:
            class_name = f"{previous_class}{group}"

    return ChatContext(
        intent="jadwal_pelajaran",
        class_name=class_name,
        day=day,
        is_active=True,
    )


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
    context: ChatContext | None = None,
    today: date | None = None,
) -> ChatResult:
    previous_context = context or ChatContext()
    normalized_message = normalize_text(message)

    if not normalized_message:
        return ChatResult(
            intent=previous_context.intent,
            intent_source=(
                "rule"
                if previous_context.intent is not None
                else None
            ),
            status="invalid_request",
            class_name=previous_context.class_name,
            day=previous_context.day,
            missing_entities=(),
            academic_year=None,
            items=(),
            message="Pesan tidak boleh kosong.",
            context=previous_context,
        )

    detected_intent = detect_rule_intent(message)

    if detected_intent is not None:
        intent = detected_intent
    elif (
        previous_context.is_active
        and previous_context.intent is not None
    ):
        # Pesan seperti "7A", "Senin", atau "A" diproses
        # sebagai lanjutan conversation engine.
        intent = previous_context.intent
    else:
        empty_context = ChatContext()

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
            context=empty_context,
        )

    merged_context = merge_schedule_context(
        message=message,
        previous_context=previous_context,
        today=today,
    )

    class_name = merged_context.class_name
    day = merged_context.day

    missing_entities: list[str] = []

    if class_name is None:
        missing_entities.append("class_name")
    else:
        class_validation = validate_class_format(class_name)

        if class_validation.error_code == "missing_group":
            missing_entities.append("class_group")
        elif not class_validation.is_valid:
            closed_context = ChatContext(
                intent=intent,
                class_name=class_validation.class_name,
                day=day,
                is_active=False,
            )

            return ChatResult(
                intent=intent,
                intent_source="rule",
                status="invalid_request",
                class_name=class_validation.class_name,
                day=day,
                missing_entities=(),
                academic_year=None,
                items=(),
                message=(
                    class_validation.message
                    or "Format kelas tidak valid."
                ),
                context=closed_context,
            )

    if day is None:
        missing_entities.append("day")

    if missing_entities:
        missing_tuple = tuple(missing_entities)

        active_context = ChatContext(
            intent=intent,
            class_name=class_name,
            day=day,
            is_active=True,
        )

        return ChatResult(
            intent=intent,
            intent_source="rule",
            status="needs_clarification",
            class_name=class_name,
            day=day,
            missing_entities=missing_tuple,
            academic_year=None,
            items=(),
            message=build_clarification_message(
                class_name=class_name,
                missing_entities=missing_tuple,
            ),
            context=active_context,
        )

    assert class_name is not None
    assert day is not None

    lookup = lookup_class_schedule(
        class_name=class_name,
        day=day,
        class_repository=class_repository,
        schedule_repository=schedule_repository,
    )

    closed_context = ChatContext(
        intent=intent,
        class_name=lookup.class_name,
        day=lookup.day,
        is_active=False,
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
            context=closed_context,
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
            context=closed_context,
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
            context=closed_context,
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
        context=closed_context,
    )