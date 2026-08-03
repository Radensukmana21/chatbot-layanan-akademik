from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


StoragePolicy = Literal[
    "full",
    "redacted",
    "metadata_only",
]


METADATA_ONLY_PLACEHOLDER = (
    "[konten tidak disimpan sesuai kebijakan privasi]"
)

RETENTION_EXPIRED_PLACEHOLDER = (
    "[konten dihapus setelah masa retensi]"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+62|62|0)8[\d\s-]{7,15}\d(?!\d)"
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

IDENTIFIER_PATTERN = re.compile(
    r"(?<!\d)\d{8,16}(?!\d)"
)


@dataclass(frozen=True, slots=True)
class PreparedMessage:
    content: str
    storage_policy: StoragePolicy
    contains_sensitive_data: bool


def redact_sensitive_text(
    content: str,
) -> tuple[str, bool]:
    """
    Menyamarkan pola sensitif yang dapat dikenali secara deterministik.

    Fungsi ini tidak mencoba menebak nama orang atau alasan kesehatan.
    Data tersebut harus menggunakan kebijakan metadata_only.
    """

    redacted = content
    contains_sensitive_data = False

    replacements = (
        (EMAIL_PATTERN, "[EMAIL]"),
        (PHONE_PATTERN, "[PHONE]"),
        (IDENTIFIER_PATTERN, "[IDENTIFIER]"),
    )

    for pattern, replacement in replacements:
        updated = pattern.sub(replacement, redacted)

        if updated != redacted:
            contains_sensitive_data = True
            redacted = updated

    return redacted, contains_sensitive_data


def prepare_message_for_storage(
    content: str,
    *,
    storage_policy: StoragePolicy,
) -> PreparedMessage:
    if storage_policy == "metadata_only":
        return PreparedMessage(
            content=METADATA_ONLY_PLACEHOLDER,
            storage_policy="metadata_only",
            contains_sensitive_data=True,
        )

    redacted_content, contains_sensitive_data = (
        redact_sensitive_text(content)
    )

    if storage_policy == "redacted":
        return PreparedMessage(
            content=redacted_content,
            storage_policy="redacted",
            contains_sensitive_data=contains_sensitive_data,
        )

    # Kebijakan full tetap melakukan pengamanan otomatis.
    # Jika nomor telepon/email/identifier terdeteksi, konten
    # diturunkan menjadi redacted.
    if contains_sensitive_data:
        return PreparedMessage(
            content=redacted_content,
            storage_policy="redacted",
            contains_sensitive_data=True,
        )

    return PreparedMessage(
        content=content,
        storage_policy="full",
        contains_sensitive_data=False,
    )