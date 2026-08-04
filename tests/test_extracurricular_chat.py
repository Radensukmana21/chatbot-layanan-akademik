from __future__ import annotations

from datetime import time

import pytest

from app.repositories.extracurricular_repository import (
    ExtracurricularRecord,
    ExtracurricularScheduleRecord,
)
from app.services.extracurricular_chat import (
    build_extracurricular_answer,
    extract_extracurricular_chat_query,
)


@pytest.mark.parametrize(
    (
        "message",
        "search_mode",
        "focus",
        "query",
    ),
    [
        (
            "Apa saja ekstrakurikuler yang tersedia?",
            "list",
            "general",
            None,
        ),
        (
            "Daftar ekskul",
            "list",
            "general",
            None,
        ),
        (
            "Jadwal Pramuka kapan?",
            "name",
            "schedule",
            "pramuka",
        ),
        (
            "Jadwal ekstrakurikuler Karate",
            "name",
            "schedule",
            "karate",
        ),
        (
            "Siapa pembina PMR?",
            "name",
            "advisor",
            "pmr",
        ),
        (
            "Pembina Paskibra siapa?",
            "name",
            "advisor",
            "paskibra",
        ),
        (
            "Pramuka dilaksanakan di mana?",
            "name",
            "location",
            "pramuka",
        ),
        (
            "Informasi ekstrakurikuler Futsal",
            "name",
            "general",
            "futsal",
        ),
    ],
)
def test_extracts_extracurricular_query(
    message: str,
    search_mode: str,
    focus: str,
    query: str | None,
) -> None:
    result = extract_extracurricular_chat_query(
        message
    )

    assert result.is_extracurricular_intent is True
    assert result.search_mode == search_mode
    assert result.focus == focus
    assert result.query == query


@pytest.mark.parametrize(
    "message",
    [
        "Jadwal kelas 7A hari Senin",
        "Siapa guru Matematika?",
        "Bu Ane mengajar apa?",
        "Cek status surat saya",
    ],
)
def test_does_not_match_other_intents(
    message: str,
) -> None:
    result = extract_extracurricular_chat_query(
        message
    )

    assert result.is_extracurricular_intent is False
    assert result.search_mode is None
    assert result.focus is None
    assert result.query is None


def test_marks_incomplete_extracurricular_query(
) -> None:
    result = extract_extracurricular_chat_query(
        "Tolong bantu tentang ekskul"
    )

    assert result.is_extracurricular_intent is True
    assert result.search_mode is None
    assert result.focus is None
    assert result.query is None


def build_pramuka_record(
) -> ExtracurricularRecord:
    return ExtracurricularRecord(
        id=1,
        name="Pramuka",
        advisor_name="Guru Pembina",
        location="Lapangan",
        description="Kegiatan kepanduan",
        schedules=(
            ExtracurricularScheduleRecord(
                day="jumat",
                start_time=time(14, 0),
                end_time=time(16, 0),
            ),
        ),
    )


def test_builds_list_answer() -> None:
    items = (
        build_pramuka_record(),
        ExtracurricularRecord(
            id=2,
            name="PMR",
            advisor_name="Guru PMR",
            location="UKS",
            description=None,
            schedules=(),
        ),
    )

    answer = build_extracurricular_answer(
        search_mode="list",
        focus="general",
        items=items,
    )

    assert answer == (
        "Ekstrakurikuler yang tersedia adalah "
        "Pramuka, PMR."
    )


def test_builds_schedule_answer() -> None:
    answer = build_extracurricular_answer(
        search_mode="name",
        focus="schedule",
        items=(build_pramuka_record(),),
    )

    assert answer == (
        "Jadwal Pramuka: Jumat "
        "pukul 14:00–16:00."
    )


def test_builds_advisor_answer() -> None:
    answer = build_extracurricular_answer(
        search_mode="name",
        focus="advisor",
        items=(build_pramuka_record(),),
    )

    assert answer == (
        "Pembina Pramuka adalah Guru Pembina."
    )


def test_builds_location_answer() -> None:
    answer = build_extracurricular_answer(
        search_mode="name",
        focus="location",
        items=(build_pramuka_record(),),
    )

    assert answer == (
        "Pramuka dilaksanakan di Lapangan."
    )


def test_builds_general_answer() -> None:
    answer = build_extracurricular_answer(
        search_mode="name",
        focus="general",
        items=(build_pramuka_record(),),
    )

    assert "Pramuka" in answer
    assert "Guru Pembina" in answer
    assert "Lapangan" in answer
    assert "Jumat pukul 14:00–16:00" in answer
    assert "Kegiatan kepanduan" in answer