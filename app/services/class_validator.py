from __future__ import annotations

from dataclasses import dataclass
import re


CLASS_FORMAT_PATTERN = re.compile(
    r"^(?P<grade>[789])(?P<group>[A-K])$"
)


@dataclass(frozen=True, slots=True)
class ClassFormatResult:
    class_name: str | None
    grade: int | None
    group: str | None
    is_valid: bool
    error_code: str | None
    message: str | None


def normalize_class_name(value: str | None) -> str | None:
    """
    Menormalisasi nama kelas.

    Contoh:
    - "8 a" -> "8A"
    - " 9k " -> "9K"
    """

    if not value:
        return None

    normalized = re.sub(r"\s+", "", value).upper()

    return normalized or None


def validate_class_format(
    value: str | None,
) -> ClassFormatResult:
    """
    Memvalidasi format kelas secara sintaksis.

    Aturan:
    - tingkat hanya 7, 8, atau 9;
    - rombel berada pada A sampai K;
    - keberadaan kelas aktif diperiksa terpisah melalui database.
    """

    class_name = normalize_class_name(value)

    if class_name is None:
        return ClassFormatResult(
            class_name=None,
            grade=None,
            group=None,
            is_valid=False,
            error_code="missing_class",
            message="Nama kelas belum diberikan.",
        )

    # Tingkat tanpa rombel, misalnya "8".
    if re.fullmatch(r"[789]", class_name):
        return ClassFormatResult(
            class_name=class_name,
            grade=int(class_name),
            group=None,
            is_valid=False,
            error_code="missing_group",
            message=(
                f"Kelas {class_name} belum lengkap. "
                "Silakan tambahkan huruf rombel, misalnya "
                f"{class_name}A."
            ),
        )

    match = CLASS_FORMAT_PATTERN.fullmatch(class_name)

    if match is None:
        return ClassFormatResult(
            class_name=class_name,
            grade=None,
            group=None,
            is_valid=False,
            error_code="invalid_class_format",
            message=(
                f"Format kelas {class_name} tidak valid. "
                "Kelas yang didukung adalah tingkat 7 sampai 9 "
                "dengan rombel A sampai K."
            ),
        )

    grade = int(match.group("grade"))
    group = match.group("group")

    return ClassFormatResult(
        class_name=class_name,
        grade=grade,
        group=group,
        is_valid=True,
        error_code=None,
        message=None,
    )