from datetime import date

import pytest

from app.nlp.entity_extractor import (
    extract_class,
    extract_day,
    extract_schedule_entities,
)
from app.nlp.normalizers import normalize_text


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("Jadwal kelas 8A hari Senin", "8A"),
        ("jadwal kelas 8 a", "8A"),
        ("jdwl kls 7b", "7B"),
        ("Jadwal VII A hari Senin", "7A"),
        ("Jadwal kelas VIII B", "8B"),
        ("Jadwal kelas IX A", "9A"),
        ("Jadwal kelas VII C", "7C"),
        ("kelas sembilan C hari Kamis", "9C"),
        ("Guru matematika kelas 8 siapa?", "8"),
        ("Info kelas sembilan", "9"),
        ("Info kelas VIII", "8"),
        ("Info kelas IX", "9"),
        ("Jadwal kelas 8Z", "8Z"),
    ],
)
def test_extract_class(raw_text: str, expected: str) -> None:
    assert extract_class(raw_text) == expected


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("hari Senin", "senin"),
        ("snin", "senin"),
        ("senen", "senin"),
        ("slasa", "selasa"),
        ("rebo", "rabu"),
        ("hari jum'at", "jumat"),
        ("saptu", "sabtu"),
        ("ahad", "minggu"),
    ],
)
def test_extract_explicit_day(raw_text: str, expected: str) -> None:
    assert extract_day(raw_text) == expected


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("jadwal hari ini", "senin"),
        ("jadwal besok", "selasa"),
        ("jadwal lusa", "rabu"),
    ],
)
def test_extract_relative_day(raw_text: str, expected: str) -> None:
    # 1 Januari 2024 adalah Senin.
    reference_date = date(2024, 1, 1)

    assert extract_day(raw_text, today=reference_date) == expected


def test_extract_schedule_entities() -> None:
    entities = extract_schedule_entities(
        "Saya tinggal di Bandung, jadwal kelas 7A hari Senin apa?"
    )

    assert entities.class_name == "7A"
    assert entities.day == "senin"


def test_substring_does_not_trigger_false_detection() -> None:
    assert extract_day("Saya tinggal di Bandung") is None
    assert extract_day("Jumlah pelajaran berapa?") is None


def test_empty_text_returns_no_entities() -> None:
    entities = extract_schedule_entities("")

    assert entities.class_name is None
    assert entities.day is None


def test_normalize_text() -> None:
    assert normalize_text("  Jadwal   Kelas 8A, Hari Senin! ") == (
        "jadwal kelas 8a hari senin"
    )