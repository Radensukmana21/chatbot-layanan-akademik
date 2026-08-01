from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta


DAY_NAMES = (
    "senin",
    "selasa",
    "rabu",
    "kamis",
    "jumat",
    "sabtu",
    "minggu",
)

DAY_ALIASES = {
    "senin": "senin",
    "senen": "senin",
    "snin": "senin",
    "selasa": "selasa",
    "slasa": "selasa",
    "slsa": "selasa",
    "rabu": "rabu",
    "rebo": "rabu",
    "rbo": "rabu",
    "kamis": "kamis",
    "kmis": "kamis",
    "jumat": "jumat",
    "jumat": "jumat",
    "jmat": "jumat",
    "sabtu": "sabtu",
    "saptu": "sabtu",
    "minggu": "minggu",
    "ahad": "minggu",
}

ROMAN_GRADES = {
    "vii": "7",
    "viii": "8",
    "ix": "9",
}

WRITTEN_GRADES = {
    "tujuh": "7",
    "delapan": "8",
    "sembilan": "9",
}


def normalize_text(value: str | None) -> str:
    """Membersihkan teks tanpa melakukan stemming."""

    if not value:
        return ""

    text = unicodedata.normalize("NFKC", value)
    text = text.casefold()

    # Jum'at dan bentuk sejenis dinormalisasi menjadi jumat.
    text = text.replace("'", "").replace("’", "")

    # Sisakan huruf, angka, dan spasi.
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def day_name_from_date(value: date) -> str:
    """Mengubah tanggal menjadi nama hari Bahasa Indonesia."""

    return DAY_NAMES[value.weekday()]


def resolve_relative_day(
    text: str | None,
    *,
    today: date | None = None,
) -> str | None:
    """Mengubah hari ini, besok, dan lusa menjadi nama hari."""

    normalized = normalize_text(text)
    reference_date = today or date.today()

    if re.search(r"\bhari ini\b", normalized):
        return day_name_from_date(reference_date)

    if re.search(r"\bbesok\b", normalized):
        return day_name_from_date(reference_date + timedelta(days=1))

    if re.search(r"\blusa\b", normalized):
        return day_name_from_date(reference_date + timedelta(days=2))

    return None