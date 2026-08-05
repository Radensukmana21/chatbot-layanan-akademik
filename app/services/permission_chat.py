from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.nlp.normalizers import normalize_text
from app.repositories.permission_request_repository import (
    PermissionStatusRecord,
)


PermissionChatIntent = Literal[
    "ajukan_surat_izin",
    "cek_status_surat",
]


@dataclass(frozen=True, slots=True)
class PermissionChatQuery:
    is_permission_intent: bool
    intent: PermissionChatIntent | None
    tracking_code: str | None


TRACKING_CODE_SEARCH_PATTERN = re.compile(
    r"\bIZN-[A-F0-9]{12}\b",
    flags=re.IGNORECASE,
)


SUBMISSION_PATTERNS = (
    re.compile(
        r"^(?:saya\s+)?"
        r"(?:(?:ingin|mau|hendak)\s+)?"
        r"(?:mengajukan|ajukan|buat|bikin)\s+"
        r"(?:surat\s+)?izin"
        r"(?:\s+(?:sakit|keperluan|"
        r"keperluan keluarga))?$"
    ),
    re.compile(
        r"^(?:saya\s+)?"
        r"(?:ingin|mau|hendak)\s+izin"
        r"(?:\s+(?:sakit|keperluan|"
        r"keperluan keluarga))?$"
    ),
    re.compile(
        r"^izin\s+"
        r"(?:sakit|keperluan|keperluan keluarga)$"
    ),
    re.compile(
        r"^pengajuan\s+(?:surat\s+)?izin$"
    ),
)


STATUS_PATTERNS = (
    re.compile(
        r"^(?:cek|periksa|lihat)\s+"
        r"status(?:\s+surat)?\s+izin"
        r"(?:\s+.*)?$"
    ),
    re.compile(
        r"^(?:bagaimana\s+)?"
        r"status(?:\s+surat)?\s+izin"
        r"(?:\s+.*)?$"
    ),
    re.compile(
        r"^(?:cek|periksa)\s+"
        r"surat\s+izin"
        r"(?:\s+.*)?$"
    ),
    re.compile(
        r"^status\s+pengajuan\s+izin"
        r"(?:\s+.*)?$"
    ),
)


def extract_tracking_code(
    message: str | None,
) -> str | None:
    if message is None:
        return None

    match = TRACKING_CODE_SEARCH_PATTERN.search(
        message
    )

    if match is None:
        return None

    return match.group(0).upper()


def extract_permission_chat_query(
    message: str | None,
) -> PermissionChatQuery:
    if message is None:
        return PermissionChatQuery(
            is_permission_intent=False,
            intent=None,
            tracking_code=None,
        )

    tracking_code = extract_tracking_code(
        message
    )

    normalized = normalize_text(message)

    if not normalized:
        return PermissionChatQuery(
            is_permission_intent=False,
            intent=None,
            tracking_code=None,
        )

    # Sebuah kode pelacakan yang dikirim sendiri
    # dianggap sebagai permintaan pemeriksaan status.
    if tracking_code is not None:
        return PermissionChatQuery(
            is_permission_intent=True,
            intent="cek_status_surat",
            tracking_code=tracking_code,
        )

    for pattern in STATUS_PATTERNS:
        if pattern.fullmatch(normalized):
            return PermissionChatQuery(
                is_permission_intent=True,
                intent="cek_status_surat",
                tracking_code=None,
            )

    for pattern in SUBMISSION_PATTERNS:
        if pattern.fullmatch(normalized):
            return PermissionChatQuery(
                is_permission_intent=True,
                intent="ajukan_surat_izin",
                tracking_code=None,
            )

    tokens = set(normalized.split())

    has_permission_terms = (
        "surat" in tokens
        and "izin" in tokens
    )

    if has_permission_terms:
        submission_terms = {
            "ajukan",
            "mengajukan",
            "pengajuan",
            "buat",
            "bikin",
        }

        status_terms = {
            "status",
            "cek",
            "periksa",
            "lihat",
        }

        if tokens.intersection(status_terms):
            return PermissionChatQuery(
                is_permission_intent=True,
                intent="cek_status_surat",
                tracking_code=None,
            )

        if tokens.intersection(submission_terms):
            return PermissionChatQuery(
                is_permission_intent=True,
                intent="ajukan_surat_izin",
                tracking_code=None,
            )

        # Pengguna menyebut surat izin, tetapi belum
        # menjelaskan ingin mengajukan atau mengecek.
        return PermissionChatQuery(
            is_permission_intent=True,
            intent=None,
            tracking_code=None,
        )

    return PermissionChatQuery(
        is_permission_intent=False,
        intent=None,
        tracking_code=None,
    )


def build_permission_submission_answer(
    *,
    tracking_code: str,
) -> str:
    return (
        "Pengajuan surat izin berhasil dibuat "
        "dengan status menunggu pemeriksaan. "
        f"Kode pelacakan Anda adalah {tracking_code}. "
        "Simpan kode tersebut untuk memeriksa status."
    )


def build_permission_status_answer(
    *,
    item: PermissionStatusRecord,
) -> str:
    status_messages = {
        "pending": "masih menunggu pemeriksaan",
        "approved": "telah disetujui",
        "rejected": "telah ditolak",
    }

    status_message = status_messages.get(
        item.status,
        f"memiliki status {item.status}",
    )

    return (
        f"Pengajuan dengan kode "
        f"{item.tracking_code} "
        f"{status_message}."
    )