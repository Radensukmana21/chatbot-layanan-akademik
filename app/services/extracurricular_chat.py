from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.nlp.normalizers import normalize_text
from app.repositories.extracurricular_repository import (
    ExtracurricularRecord,
)


ExtracurricularSearchMode = Literal[
    "list",
    "name",
]

ExtracurricularFocus = Literal[
    "general",
    "schedule",
    "advisor",
    "location",
]


@dataclass(frozen=True, slots=True)
class ExtracurricularChatQuery:
    is_extracurricular_intent: bool
    search_mode: ExtracurricularSearchMode | None
    focus: ExtracurricularFocus | None
    query: str | None


EXTRACURRICULAR_TERMS = {
    "ekstrakurikuler",
    "ekstrakulikuler",
    "ekskul",
    "eskul",
    "ekstra",
}


KNOWN_EXTRACURRICULAR_NAMES = {
    "pramuka",
    "futsal",
    "pmr",
    "paskibra",
    "basket",
    "tari",
    "paduan suara",
    "karate",
}


LIST_PATTERNS = (
    re.compile(
        r"^(?:apa saja|sebutkan|daftar)"
        r"(?: kegiatan)? "
        r"(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra)"
        r"(?: yang tersedia)?"
        r"(?: di sekolah)?$"
    ),
    re.compile(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra)"
        r"(?: apa saja)?"
        r"(?: yang tersedia)?"
        r"(?: di sekolah)?$"
    ),
    re.compile(
        r"^informasi "
        r"(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra)$"
    ),
)


EXPLICIT_SCHEDULE_PATTERNS = (
    re.compile(
        r"^jadwal "
        r"(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+?)(?: kapan)?$"
    ),
    re.compile(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+?) "
        r"(?:jadwalnya kapan|kapan|hari apa)$"
    ),
)


ADVISOR_PATTERNS = (
    re.compile(
        r"^siapa pembina "
        r"(?P<query>.+)$"
    ),
    re.compile(
        r"^pembina "
        r"(?P<query>.+?) siapa$"
    ),
    re.compile(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+?) "
        r"(?:dibina oleh siapa|pembinanya siapa)$"
    ),
)


LOCATION_PATTERNS = (
    re.compile(
        r"^(?P<query>.+?) "
        r"(?:dilaksanakan|diadakan|latihan)"
        r"(?:nya)? di mana$"
    ),
    re.compile(
        r"^lokasi "
        r"(?P<query>.+?)"
        r"(?: di mana)?$"
    ),
    re.compile(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+?) "
        r"(?:lokasinya di mana|di mana)$"
    ),
)


GENERAL_PATTERNS = (
    re.compile(
        r"^(?:info|informasi) "
        r"(?:tentang )?"
        r"(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+)$"
    ),
    re.compile(
        r"^(?:info|informasi) "
        r"(?P<query>.+)$"
    ),
    re.compile(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra) "
        r"(?P<query>.+)$"
    ),
)


GENERIC_SCHEDULE_PATTERN = re.compile(
    r"^jadwal (?P<query>.+?)(?: kapan)?$"
)


def _clean_query(value: str) -> str:
    query = value.strip()

    query = re.sub(
        r"^(?:ekstrakurikuler|ekstrakulikuler|"
        r"ekskul|eskul|ekstra)\s+",
        "",
        query,
    )

    query = re.sub(
        r"\s+(?:jadwalnya|kapan|hari apa)$",
        "",
        query,
    )

    return query.strip()


def _matches_known_name(query: str) -> bool:
    return query in KNOWN_EXTRACURRICULAR_NAMES


def extract_extracurricular_chat_query(
    message: str | None,
) -> ExtracurricularChatQuery:
    normalized = normalize_text(message or "")

    if not normalized:
        return ExtracurricularChatQuery(
            is_extracurricular_intent=False,
            search_mode=None,
            focus=None,
            query=None,
        )

    for pattern in LIST_PATTERNS:
        if pattern.fullmatch(normalized):
            return ExtracurricularChatQuery(
                is_extracurricular_intent=True,
                search_mode="list",
                focus="general",
                query=None,
            )

    for pattern in EXPLICIT_SCHEDULE_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            query = _clean_query(
                match.group("query")
            )

            return ExtracurricularChatQuery(
                is_extracurricular_intent=True,
                search_mode="name",
                focus="schedule",
                query=query or None,
            )

    generic_schedule_match = (
        GENERIC_SCHEDULE_PATTERN.fullmatch(
            normalized
        )
    )

    if generic_schedule_match is not None:
        query = _clean_query(
            generic_schedule_match.group("query")
        )

        if _matches_known_name(query):
            return ExtracurricularChatQuery(
                is_extracurricular_intent=True,
                search_mode="name",
                focus="schedule",
                query=query,
            )

    for pattern in ADVISOR_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            query = _clean_query(
                match.group("query")
            )

            return ExtracurricularChatQuery(
                is_extracurricular_intent=True,
                search_mode="name",
                focus="advisor",
                query=query or None,
            )

    for pattern in LOCATION_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            query = _clean_query(
                match.group("query")
            )

            if (
                any(
                    term in normalized.split()
                    for term
                    in EXTRACURRICULAR_TERMS
                )
                or _matches_known_name(query)
            ):
                return ExtracurricularChatQuery(
                    is_extracurricular_intent=True,
                    search_mode="name",
                    focus="location",
                    query=query or None,
                )

    for pattern in GENERAL_PATTERNS:
        match = pattern.fullmatch(normalized)

        if match is not None:
            query = _clean_query(
                match.group("query")
            )

            if (
                any(
                    term in normalized.split()
                    for term
                    in EXTRACURRICULAR_TERMS
                )
                or _matches_known_name(query)
            ):
                return ExtracurricularChatQuery(
                    is_extracurricular_intent=True,
                    search_mode="name",
                    focus="general",
                    query=query or None,
                )

    tokens = set(normalized.split())

    if tokens.intersection(
        EXTRACURRICULAR_TERMS
    ):
        return ExtracurricularChatQuery(
            is_extracurricular_intent=True,
            search_mode=None,
            focus=None,
            query=None,
        )

    return ExtracurricularChatQuery(
        is_extracurricular_intent=False,
        search_mode=None,
        focus=None,
        query=None,
    )


def _format_schedule(
    item: ExtracurricularRecord,
) -> str:
    if not item.schedules:
        return "jadwal belum tersedia"

    schedules = [
        (
            f"{schedule.day.title()} "
            f"pukul "
            f"{schedule.start_time.strftime('%H:%M')}"
            f"–"
            f"{schedule.end_time.strftime('%H:%M')}"
        )
        for schedule in item.schedules
    ]

    return "; ".join(schedules)


def build_extracurricular_answer(
    *,
    search_mode: ExtracurricularSearchMode,
    focus: ExtracurricularFocus,
    items: tuple[ExtracurricularRecord, ...],
) -> str:
    if search_mode == "list":
        names = ", ".join(
            item.name
            for item in items
        )

        return (
            "Ekstrakurikuler yang tersedia adalah "
            f"{names}."
        )

    if len(items) > 1:
        names = ", ".join(
            item.name
            for item in items
        )

        return (
            "Ditemukan beberapa ekstrakurikuler "
            f"yang sesuai: {names}."
        )

    item = items[0]

    if focus == "schedule":
        return (
            f"Jadwal {item.name}: "
            f"{_format_schedule(item)}."
        )

    if focus == "advisor":
        advisor = (
            item.advisor_name
            or "belum tersedia"
        )

        return (
            f"Pembina {item.name} adalah "
            f"{advisor}."
        )

    if focus == "location":
        location = (
            item.location
            or "belum tersedia"
        )

        return (
            f"{item.name} dilaksanakan di "
            f"{location}."
        )

    advisor = (
        item.advisor_name
        or "belum tersedia"
    )

    location = (
        item.location
        or "belum tersedia"
    )

    description = (
        f" {item.description}."
        if item.description
        else ""
    )

    return (
        f"{item.name} dibina oleh {advisor}, "
        f"dilaksanakan di {location}, dengan "
        f"{_format_schedule(item)}."
        f"{description}"
    )