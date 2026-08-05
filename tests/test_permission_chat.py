from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.permission_request_repository import (
    PermissionStatusRecord,
)
from app.services.permission_chat import (
    build_permission_status_answer,
    build_permission_submission_answer,
    extract_permission_chat_query,
    extract_tracking_code,
)


@pytest.mark.parametrize(
    (
        "message",
        "expected_intent",
        "expected_code",
    ),
    [
        (
            "Saya ingin mengajukan surat izin",
            "ajukan_surat_izin",
            None,
        ),
        (
            "Buat surat izin sakit",
            "ajukan_surat_izin",
            None,
        ),
        (
            "Saya mau izin keperluan keluarga",
            "ajukan_surat_izin",
            None,
        ),
        (
            "Pengajuan surat izin",
            "ajukan_surat_izin",
            None,
        ),
        (
            "Cek status surat izin",
            "cek_status_surat",
            None,
        ),
        (
            (
                "Cek status surat "
                "IZN-A1B2C3D4E5F6"
            ),
            "cek_status_surat",
            "IZN-A1B2C3D4E5F6",
        ),
        (
            "izn-a1b2c3d4e5f6",
            "cek_status_surat",
            "IZN-A1B2C3D4E5F6",
        ),
    ],
)
def test_extracts_permission_intent(
    message: str,
    expected_intent: str,
    expected_code: str | None,
) -> None:
    result = extract_permission_chat_query(
        message
    )

    assert result.is_permission_intent is True
    assert result.intent == expected_intent
    assert result.tracking_code == expected_code


def test_marks_ambiguous_permission_query(
) -> None:
    result = extract_permission_chat_query(
        "Informasi surat izin"
    )

    assert result.is_permission_intent is True
    assert result.intent is None
    assert result.tracking_code is None


@pytest.mark.parametrize(
    "message",
    [
        "Jadwal kelas 7A hari Senin",
        "Siapa guru Matematika?",
        "Jadwal Pramuka kapan?",
        "Apa saja ekstrakurikuler?",
    ],
)
def test_does_not_match_other_intents(
    message: str,
) -> None:
    result = extract_permission_chat_query(
        message
    )

    assert result.is_permission_intent is False
    assert result.intent is None
    assert result.tracking_code is None


def test_does_not_extract_invalid_tracking_code(
) -> None:
    assert (
        extract_tracking_code(
            "Cek status IZN-123"
        )
        is None
    )


def test_builds_submission_answer() -> None:
    answer = build_permission_submission_answer(
        tracking_code="IZN-A1B2C3D4E5F6",
    )

    assert "berhasil dibuat" in answer
    assert "menunggu pemeriksaan" in answer
    assert "IZN-A1B2C3D4E5F6" in answer

    assert "nama" not in answer.lower()
    assert "telepon" not in answer.lower()


@pytest.mark.parametrize(
    (
        "status",
        "expected_text",
    ),
    [
        (
            "pending",
            "masih menunggu pemeriksaan",
        ),
        (
            "approved",
            "telah disetujui",
        ),
        (
            "rejected",
            "telah ditolak",
        ),
    ],
)
def test_builds_safe_status_answer(
    status: str,
    expected_text: str,
) -> None:
    item = PermissionStatusRecord(
        tracking_code="IZN-A1B2C3D4E5F6",
        status=status,
        submitted_at=datetime(
            2026,
            8,
            5,
            10,
            0,
        ),
        reviewed_at=None,
    )

    answer = build_permission_status_answer(
        item=item
    )

    assert "IZN-A1B2C3D4E5F6" in answer
    assert expected_text in answer

    assert "student" not in answer.lower()
    assert "siswa contoh" not in answer.lower()
    assert "0812" not in answer