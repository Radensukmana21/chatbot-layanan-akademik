from __future__ import annotations

from dataclasses import dataclass
import re
import secrets
from typing import Literal

from app.models import PermissionRequest
from app.nlp.normalizers import normalize_text
from app.repositories.permission_request_repository import (
    MultipleActiveClassesError,
    PermissionRequestRepository,
    PermissionStatusRecord,
)


PermissionSubmissionStatus = Literal[
    "created",
    "invalid_name",
    "invalid_class",
    "invalid_permission_type",
    "invalid_description",
    "invalid_phone_number",
    "configuration_error",
]

PermissionLookupStatus = Literal[
    "ok",
    "invalid_code",
    "not_found",
]


@dataclass(frozen=True, slots=True)
class PermissionSubmissionResult:
    status: PermissionSubmissionStatus
    request: PermissionRequest | None
    message: str


@dataclass(frozen=True, slots=True)
class PermissionLookupResult:
    status: PermissionLookupStatus
    item: PermissionStatusRecord | None
    message: str


TRACKING_CODE_PATTERN = re.compile(
    r"^IZN-[A-F0-9]{12}$"
)

CLASS_NAME_PATTERN = re.compile(
    r"^[7-9][A-K]$"
)

PHONE_NUMBER_PATTERN = re.compile(
    r"^(?:62|0)8[0-9]{8,12}$"
)

PERMISSION_TYPE_ALIASES = {
    "sakit": "sakit",
    "keperluan": "keperluan",
    "keperluan keluarga": "keperluan",
}


def normalize_class_name(
    value: str,
) -> str:
    normalized = normalize_text(value)
    normalized = re.sub(
        r"^kelas\s+",
        "",
        normalized,
    )
    normalized = re.sub(
        r"\s+",
        "",
        normalized,
    )

    return normalized.upper()


def normalize_phone_number(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    compact = re.sub(
        r"[\s().-]+",
        "",
        value.strip(),
    )

    if not compact:
        return None

    if compact.startswith("+62"):
        compact = "62" + compact[3:]

    if PHONE_NUMBER_PATTERN.fullmatch(
        compact
    ) is None:
        raise ValueError(
            "Format nomor telepon tidak valid."
        )

    return compact


def generate_tracking_code(
    *,
    repository: PermissionRequestRepository,
) -> str:
    for _ in range(20):
        random_part = secrets.token_hex(
            6
        ).upper()

        tracking_code = (
            f"IZN-{random_part}"
        )

        if not repository.tracking_code_exists(
            tracking_code=tracking_code
        ):
            return tracking_code

    raise RuntimeError(
        "Gagal membuat kode pelacakan unik."
    )


def submit_permission_request(
    *,
    student_name: str,
    class_name: str,
    permission_type: str,
    description: str,
    phone_number: str | None,
    repository: PermissionRequestRepository,
    source_key: str | None = None,
) -> PermissionSubmissionResult:
    cleaned_name = " ".join(
        student_name.split()
    )

    if len(cleaned_name) < 2:
        return PermissionSubmissionResult(
            status="invalid_name",
            request=None,
            message=(
                "Nama siswa minimal dua karakter."
            ),
        )

    normalized_class = normalize_class_name(
        class_name
    )

    if CLASS_NAME_PATTERN.fullmatch(
        normalized_class
    ) is None:
        return PermissionSubmissionResult(
            status="invalid_class",
            request=None,
            message=(
                "Format kelas tidak valid. "
                "Contoh kelas yang benar: 7A."
            ),
        )

    normalized_type = normalize_text(
        permission_type
    )

    canonical_type = (
        PERMISSION_TYPE_ALIASES.get(
            normalized_type
        )
    )

    if canonical_type is None:
        return PermissionSubmissionResult(
            status="invalid_permission_type",
            request=None,
            message=(
                "Jenis izin harus berupa "
                "'sakit' atau 'keperluan'."
            ),
        )

    cleaned_description = " ".join(
        description.split()
    )

    if len(cleaned_description) < 3:
        return PermissionSubmissionResult(
            status="invalid_description",
            request=None,
            message=(
                "Keterangan izin minimal "
                "tiga karakter."
            ),
        )

    try:
        normalized_phone = (
            normalize_phone_number(
                phone_number
            )
        )
    except ValueError:
        return PermissionSubmissionResult(
            status="invalid_phone_number",
            request=None,
            message=(
                "Format nomor telepon tidak valid."
            ),
        )

    try:
        school_class = (
            repository.find_active_class(
                class_name=normalized_class
            )
        )
    except MultipleActiveClassesError:
        return PermissionSubmissionResult(
            status="configuration_error",
            request=None,
            message=(
                "Konfigurasi kelas aktif "
                "sedang bermasalah."
            ),
        )

    if school_class is None:
        return PermissionSubmissionResult(
            status="invalid_class",
            request=None,
            message=(
                "Kelas tidak ditemukan pada "
                "tahun ajaran aktif."
            ),
        )

    if source_key is not None:
        existing_request = (
            repository.get_by_source_key(
                source_key=source_key
            )
        )

        if existing_request is not None:
            return PermissionSubmissionResult(
                status="created",
                request=existing_request,
                message=(
                    "Pengajuan surat izin sebelumnya "
                    "sudah berhasil dibuat. "
                    "Gunakan kode pelacakan yang sama "
                    "untuk memeriksa status."
                ),
            )

    tracking_code = generate_tracking_code(
        repository=repository
    )

    request = repository.create(
        tracking_code=tracking_code,
        school_class_id=school_class.id,
        class_name=school_class.class_name,
        student_name=cleaned_name,
        permission_type=canonical_type,
        description=cleaned_description,
        phone_number=normalized_phone,
        source_key=source_key,
    )

    return PermissionSubmissionResult(
        status="created",
        request=request,
        message=(
            "Pengajuan surat izin berhasil dibuat. "
            "Simpan kode pelacakan untuk "
            "memeriksa status."
        ),
    )


def lookup_permission_status(
    *,
    tracking_code: str,
    repository: PermissionRequestRepository,
) -> PermissionLookupResult:
    normalized_code = (
        tracking_code.strip().upper()
    )

    if TRACKING_CODE_PATTERN.fullmatch(
        normalized_code
    ) is None:
        return PermissionLookupResult(
            status="invalid_code",
            item=None,
            message=(
                "Format kode pelacakan tidak valid."
            ),
        )

    item = repository.get_status(
        tracking_code=normalized_code
    )

    if item is None:
        return PermissionLookupResult(
            status="not_found",
            item=None,
            message=(
                "Pengajuan dengan kode tersebut "
                "tidak ditemukan."
            ),
        )

    return PermissionLookupResult(
        status="ok",
        item=item,
        message=(
            "Status pengajuan berhasil ditemukan."
        ),
    )