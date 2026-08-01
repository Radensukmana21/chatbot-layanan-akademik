from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from app.nlp.normalizers import (
    DAY_ALIASES,
    ROMAN_GRADES,
    WRITTEN_GRADES,
    normalize_text,
    resolve_relative_day,
)


@dataclass(frozen=True, slots=True)
class ScheduleEntities:
    class_name: str | None
    day: str | None


def extract_class(text: str | None) -> str | None:
    """
    Mengambil kelas dari variasi seperti:
    - 8A
    - 8 A
    - kelas 8A
    - kls 7b
    - VII A
    - kelas sembilan C

    Jika hanya tingkat yang tersedia, misalnya "kelas 8",
    fungsi mengembalikan "8" agar conversation engine dapat
    meminta rombel secara terpisah.
    """

    normalized = normalize_text(text)

    if not normalized:
        return None

    # Bentuk angka lengkap: 8A, kelas 8 A, kls 7b.
    numeric_match = re.search(
        r"\b(?:kelas|kls)?\s*([789])\s*([a-z])\b",
        normalized,
    )
    if numeric_match:
        grade, group = numeric_match.groups()
        return f"{grade}{group.upper()}"

    # Bentuk angka Romawi: VII A, kelas VIII B.
    roman_match = re.search(
        r"\b(?:kelas|kls)?\s*(viii|vii|ix)\b\s*([a-z])\b",
        normalized,
    )
    if roman_match:
        grade_roman, group = roman_match.groups()
        grade = ROMAN_GRADES[grade_roman]
        return f"{grade}{group.upper()}"

    # Bentuk tulisan: kelas sembilan A.
    written_match = re.search(
        r"\b(?:kelas|kls)?\s*(tujuh|delapan|sembilan)\s*([a-z])\b",
        normalized,
    )
    if written_match:
        grade_word, group = written_match.groups()
        grade = WRITTEN_GRADES[grade_word]
        return f"{grade}{group.upper()}"

    # Tingkat tanpa rombel hanya diterima jika didahului kelas/kls.
    partial_numeric = re.search(
        r"\b(?:kelas|kls)\s*([789])\b",
        normalized,
    )
    if partial_numeric:
        return partial_numeric.group(1)

    partial_roman = re.search(
        r"\b(?:kelas|kls)\s*(viii|vii|ix)\b",
        normalized,
    )
    if partial_roman:
        return ROMAN_GRADES[partial_roman.group(1)]

    partial_written = re.search(
        r"\b(?:kelas|kls)\s*(tujuh|delapan|sembilan)\b",
        normalized,
    )
    if partial_written:
        return WRITTEN_GRADES[partial_written.group(1)]

    return None


def extract_day(
    text: str | None,
    *,
    today: date | None = None,
) -> str | None:
    """
    Mengambil nama hari eksplisit atau hari relatif.

    Pencarian dilakukan per token, bukan substring. Karena itu,
    kata seperti 'Bandung' dan 'jumlah' tidak akan dianggap hari.
    """

    relative_day = resolve_relative_day(text, today=today)
    if relative_day:
        return relative_day

    normalized = normalize_text(text)

    for token in normalized.split():
        canonical_day = DAY_ALIASES.get(token)
        if canonical_day:
            return canonical_day

    return None


def extract_schedule_entities(
    text: str | None,
    *,
    today: date | None = None,
) -> ScheduleEntities:
    """Mengambil entitas utama untuk permintaan jadwal pelajaran."""

    return ScheduleEntities(
        class_name=extract_class(text),
        day=extract_day(text, today=today),
    )