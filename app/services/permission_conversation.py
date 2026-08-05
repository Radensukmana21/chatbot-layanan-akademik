from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.chatbot_models import PermissionDraft
from app.nlp.normalizers import normalize_text
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from app.repositories.permission_request_repository import (
    MultipleActiveClassesError,
    PermissionRequestRepository,
)
from app.services.permission_request_service import (
    CLASS_NAME_PATTERN,
    PERMISSION_TYPE_ALIASES,
    normalize_class_name,
    normalize_phone_number,
)


PermissionFlowStatus = Literal[
    "needs_input",
    "invalid_input",
    "ready_for_confirmation",
    "confirmed",
    "cancelled",
    "expired",
]


@dataclass(frozen=True, slots=True)
class PermissionFlowResult:
    status: PermissionFlowStatus
    message: str
    draft: PermissionDraft | None
    should_submit: bool = False


CANCEL_TERMS = {
    "batal",
    "batalkan",
    "cancel",
    "berhenti",
}

SKIP_PHONE_TERMS = {
    "-",
    "lewati",
    "skip",
    "tidak ada",
    "tidak punya",
    "tanpa nomor",
}

CONFIRM_TERMS = {
    "ya",
    "iya",
    "yes",
    "setuju",
    "konfirmasi",
    "kirim",
}

REJECT_CONFIRMATION_TERMS = {
    "tidak",
    "tidak jadi",
    "jangan",
    "batal",
    "batalkan",
}


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _prompt_for_step(step: str) -> str:
    prompts = {
        "student_name": (
            "Silakan masukkan nama siswa "
            "yang mengajukan izin."
        ),
        "class_name": (
            "Masukkan kelas siswa. "
            "Contohnya: 7A."
        ),
        "permission_type": (
            "Pilih jenis izin: "
            "'sakit' atau 'keperluan'."
        ),
        "description": (
            "Tuliskan keterangan singkat "
            "untuk pengajuan izin."
        ),
        "phone_number": (
            "Masukkan nomor telepon yang dapat "
            "dihubungi, atau ketik 'lewati' "
            "jika tidak ingin mengisinya."
        ),
        "confirmation": (
            "Ketik 'YA' untuk mengirim pengajuan "
            "atau 'BATAL' untuk membatalkannya."
        ),
    }

    try:
        return prompts[step]
    except KeyError as exc:
        raise ValueError(
            f"Langkah draft tidak dikenal: {step!r}."
        ) from exc


def _build_confirmation_message(
    draft: PermissionDraft,
) -> str:
    phone_status = (
        "sudah diisi"
        if draft.phone_number
        else "tidak diisi"
    )

    return (
        "Periksa kembali data pengajuan:\n"
        f"- Nama siswa: {draft.student_name}\n"
        f"- Kelas: {draft.class_name}\n"
        f"- Jenis izin: {draft.permission_type}\n"
        "- Keterangan: sudah diisi\n"
        f"- Nomor telepon: {phone_status}\n\n"
        "Ketik 'YA' untuk mengirim pengajuan "
        "atau 'BATAL' untuk membatalkannya."
    )


def start_permission_conversation(
    *,
    conversation_id: str,
    draft_repository: PermissionDraftRepository,
    now: datetime | None = None,
) -> PermissionFlowResult:
    draft = draft_repository.start(
        conversation_id=conversation_id,
        now=now,
    )

    return PermissionFlowResult(
        status="needs_input",
        message=_prompt_for_step(
            "student_name"
        ),
        draft=draft,
    )


def process_permission_draft_input(
    *,
    conversation_id: str,
    message: str,
    draft_repository: PermissionDraftRepository,
    permission_repository: PermissionRequestRepository,
    now: datetime | None = None,
) -> PermissionFlowResult:
    draft = draft_repository.get_active(
        conversation_id=conversation_id,
        now=now,
    )

    if draft is None:
        return PermissionFlowResult(
            status="expired",
            message=(
                "Draft pengajuan tidak ditemukan "
                "atau sudah kedaluwarsa. "
                "Silakan mulai pengajuan baru."
            ),
            draft=None,
        )

    cleaned_message = _compact_text(message)
    normalized_message = normalize_text(
        cleaned_message
    )

    if normalized_message in CANCEL_TERMS:
        draft_repository.delete(draft)

        return PermissionFlowResult(
            status="cancelled",
            message=(
                "Pengajuan surat izin dibatalkan. "
                "Data sementara telah dihapus."
            ),
            draft=None,
        )

    if not cleaned_message:
        return PermissionFlowResult(
            status="invalid_input",
            message=(
                "Jawaban tidak boleh kosong. "
                + _prompt_for_step(draft.step)
            ),
            draft=draft,
        )

    if draft.step == "student_name":
        if len(cleaned_message) < 2:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Nama siswa minimal dua karakter."
                ),
                draft=draft,
            )

        if len(cleaned_message) > 255:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Nama siswa maksimal "
                    "255 karakter."
                ),
                draft=draft,
            )

        draft.student_name = cleaned_message
        draft.step = "class_name"

        draft_repository.save(
            draft,
            now=now,
        )

        return PermissionFlowResult(
            status="needs_input",
            message=_prompt_for_step(
                "class_name"
            ),
            draft=draft,
        )

    if draft.step == "class_name":
        normalized_class = normalize_class_name(
            cleaned_message
        )

        if CLASS_NAME_PATTERN.fullmatch(
            normalized_class
        ) is None:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Format kelas tidak valid. "
                    "Contoh kelas yang benar: 7A."
                ),
                draft=draft,
            )

        try:
            school_class = (
                permission_repository.find_active_class(
                    class_name=normalized_class
                )
            )
        except MultipleActiveClassesError:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Konfigurasi kelas aktif "
                    "sedang bermasalah. "
                    "Silakan hubungi administrator."
                ),
                draft=draft,
            )

        if school_class is None:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Kelas tidak ditemukan pada "
                    "tahun ajaran aktif. "
                    "Silakan masukkan kelas lain."
                ),
                draft=draft,
            )

        draft.class_name = (
            school_class.class_name
        )
        draft.step = "permission_type"

        draft_repository.save(
            draft,
            now=now,
        )

        return PermissionFlowResult(
            status="needs_input",
            message=_prompt_for_step(
                "permission_type"
            ),
            draft=draft,
        )

    if draft.step == "permission_type":
        canonical_type = (
            PERMISSION_TYPE_ALIASES.get(
                normalized_message
            )
        )

        if canonical_type is None:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Jenis izin harus berupa "
                    "'sakit' atau 'keperluan'."
                ),
                draft=draft,
            )

        draft.permission_type = canonical_type
        draft.step = "description"

        draft_repository.save(
            draft,
            now=now,
        )

        return PermissionFlowResult(
            status="needs_input",
            message=_prompt_for_step(
                "description"
            ),
            draft=draft,
        )

    if draft.step == "description":
        if len(cleaned_message) < 3:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Keterangan izin minimal "
                    "tiga karakter."
                ),
                draft=draft,
            )

        if len(cleaned_message) > 2000:
            return PermissionFlowResult(
                status="invalid_input",
                message=(
                    "Keterangan izin maksimal "
                    "2000 karakter."
                ),
                draft=draft,
            )

        draft.description = cleaned_message
        draft.step = "phone_number"

        draft_repository.save(
            draft,
            now=now,
        )

        return PermissionFlowResult(
            status="needs_input",
            message=_prompt_for_step(
                "phone_number"
            ),
            draft=draft,
        )

    if draft.step == "phone_number":
        if normalized_message in SKIP_PHONE_TERMS:
            normalized_phone = None
        else:
            try:
                normalized_phone = (
                    normalize_phone_number(
                        cleaned_message
                    )
                )
            except ValueError:
                return PermissionFlowResult(
                    status="invalid_input",
                    message=(
                        "Format nomor telepon "
                        "tidak valid. Gunakan nomor "
                        "seperti 081234567890 atau "
                        "ketik 'lewati'."
                    ),
                    draft=draft,
                )

        draft.phone_number = normalized_phone
        draft.step = "confirmation"
        draft.awaiting_confirmation = True

        draft_repository.save(
            draft,
            now=now,
        )

        return PermissionFlowResult(
            status="ready_for_confirmation",
            message=_build_confirmation_message(
                draft
            ),
            draft=draft,
        )

    if draft.step == "confirmation":
        if normalized_message in CONFIRM_TERMS:
            draft_repository.save(
                draft,
                now=now,
            )

            return PermissionFlowResult(
                status="confirmed",
                message=(
                    "Data pengajuan telah "
                    "dikonfirmasi dan siap dikirim."
                ),
                draft=draft,
                should_submit=True,
            )

        if (
            normalized_message
            in REJECT_CONFIRMATION_TERMS
        ):
            draft_repository.delete(draft)

            return PermissionFlowResult(
                status="cancelled",
                message=(
                    "Pengajuan surat izin dibatalkan. "
                    "Data sementara telah dihapus."
                ),
                draft=None,
            )

        return PermissionFlowResult(
            status="invalid_input",
            message=(
                "Jawaban konfirmasi tidak dikenali. "
                "Ketik 'YA' untuk mengirim atau "
                "'BATAL' untuk membatalkan."
            ),
            draft=draft,
        )

    raise ValueError(
        f"Langkah draft tidak dikenal: "
        f"{draft.step!r}."
    )