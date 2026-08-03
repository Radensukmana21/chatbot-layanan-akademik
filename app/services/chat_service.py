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
from app.repositories.teacher_repository import (
    TeacherRepository,
)
from app.services.teacher_chat import (
    build_teacher_answer,
    extract_teacher_chat_query,
)
from app.services.teacher_lookup import (
    TeacherInformation,
    TeacherSearchMode,
    lookup_teacher_information,
)
from app.services.class_validator import validate_class_format
from app.services.schedule_lookup import lookup_class_schedule


ChatIntent = Literal[
    "jadwal_pelajaran",
    "informasi_guru",
]

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

    teacher_search_mode: TeacherSearchMode | None = None
    teacher_query: str | None = None
    teacher_items: tuple[TeacherInformation, ...] = ()

def detect_rule_intent(
    message: str | None,
) -> ChatIntent | None:
    normalized = normalize_text(message)

    if not normalized:
        return None

    tokens = set(normalized.split())

    if "jadwal" in tokens:
        return "jadwal_pelajaran"

    if re.search(r"\bbelajar\s+apa\b", normalized):
        return "jadwal_pelajaran"

    teacher_query = extract_teacher_chat_query(message)

    if teacher_query.is_teacher_intent:
        return "informasi_guru"

    return None

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

def extract_grade_reply(
    message: str | None,
) -> str | None:
    """
    Mengambil jawaban tingkat pendek pada percakapan aktif.

    Contoh:
    - 7
    - kelas 8
    - kls 9
    - tingkat 7
    """

    normalized = normalize_text(message)

    match = re.fullmatch(
        r"(?:kelas|kls|tingkat)?\s*([789])",
        normalized,
    )

    if match is None:
        return None

    return match.group(1)


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

    # Jawaban angka tunggal hanya dianggap sebagai tingkat
    # ketika conversation jadwal sedang aktif dan kelas belum ada.
    if (
        extracted.class_name is None
        and use_previous_context
        and previous_class is None
    ):
        grade = extract_grade_reply(message)

        if grade is not None:
            class_name = grade

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
    teacher_repository: TeacherRepository,
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

    if intent == "informasi_guru":
            teacher_query = extract_teacher_chat_query(
                message
            )

            closed_context = ChatContext(
                intent="informasi_guru",
                is_active=False,
            )

            if (
                teacher_query.search_mode is None
                or teacher_query.query is None
            ):
                return ChatResult(
                    intent="informasi_guru",
                    intent_source="rule",
                    status="invalid_request",
                    class_name=None,
                    day=None,
                    missing_entities=(),
                    academic_year=None,
                    items=(),
                    message=(
                        "Sebutkan nama guru atau mata pelajaran. "
                        "Contohnya: 'Bu Ane mengajar apa?' atau "
                        "'Siapa guru Matematika?'."
                    ),
                    context=closed_context,
                )

            teacher_lookup = lookup_teacher_information(
                query=teacher_query.query,
                search_mode=teacher_query.search_mode,
                class_repository=class_repository,
                teacher_repository=teacher_repository,
            )

            if teacher_lookup.status == "not_found":
                return ChatResult(
                    intent="informasi_guru",
                    intent_source="rule",
                    status="not_found",
                    class_name=None,
                    day=None,
                    missing_entities=(),
                    academic_year=(
                        teacher_lookup.academic_year
                    ),
                    items=(),
                    message=teacher_lookup.message,
                    context=closed_context,
                    teacher_search_mode=(
                        teacher_query.search_mode
                    ),
                    teacher_query=teacher_query.query,
                )

            if teacher_lookup.status in {
                "no_active_academic_year",
                "configuration_error",
            }:
                return ChatResult(
                    intent="informasi_guru",
                    intent_source="rule",
                    status="unavailable",
                    class_name=None,
                    day=None,
                    missing_entities=(),
                    academic_year=None,
                    items=(),
                    message=(
                        "Data guru sedang tidak tersedia. "
                        "Silakan hubungi administrator sekolah."
                    ),
                    context=closed_context,
                    teacher_search_mode=(
                        teacher_query.search_mode
                    ),
                    teacher_query=teacher_query.query,
                )

            if teacher_lookup.status != "ok":
                return ChatResult(
                    intent="informasi_guru",
                    intent_source="rule",
                    status="invalid_request",
                    class_name=None,
                    day=None,
                    missing_entities=(),
                    academic_year=(
                        teacher_lookup.academic_year
                    ),
                    items=(),
                    message=teacher_lookup.message,
                    context=closed_context,
                    teacher_search_mode=(
                        teacher_query.search_mode
                    ),
                    teacher_query=teacher_query.query,
                )

            answer = build_teacher_answer(
                search_mode=teacher_query.search_mode,
                query=teacher_query.query,
                items=teacher_lookup.items,
            )

            return ChatResult(
                intent="informasi_guru",
                intent_source="rule",
                status="answered",
                class_name=None,
                day=None,
                missing_entities=(),
                academic_year=(
                    teacher_lookup.academic_year
                ),
                items=(),
                message=answer,
                context=closed_context,
                teacher_search_mode=(
                    teacher_query.search_mode
                ),
                teacher_query=teacher_query.query,
                teacher_items=teacher_lookup.items,
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