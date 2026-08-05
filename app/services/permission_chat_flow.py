from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models import PermissionRequest
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from app.repositories.permission_request_repository import (
    PermissionRequestRepository,
)
from app.services.permission_chat import (
    build_permission_submission_answer,
    extract_permission_chat_query,
)
from app.services.permission_conversation import (
    process_permission_draft_input,
    start_permission_conversation,
)
from app.services.permission_request_service import (
    submit_permission_request,
)


PermissionChatResponseStatus = Literal[
    "answered",
    "needs_clarification",
    "invalid_request",
    "unavailable",
]


@dataclass(frozen=True, slots=True)
class PermissionChatFlowResult:
    status: PermissionChatResponseStatus
    message: str
    missing_entities: tuple[str, ...]
    request: PermissionRequest | None = None


def _missing_entity(
    step: str | None,
) -> tuple[str, ...]:
    if step is None:
        return ()

    return (step,)


def handle_permission_submission_chat(
    *,
    conversation_id: str,
    message: str,
    draft_repository: PermissionDraftRepository,
    permission_repository: PermissionRequestRepository,
) -> PermissionChatFlowResult | None:
    stored_draft = (
        draft_repository.get_by_conversation_id(
            conversation_id=conversation_id
        )
    )

    permission_query = (
        extract_permission_chat_query(message)
    )

    # Tidak ada draft dan pesan bukan permintaan
    # pengajuan surat: lanjutkan ke intent biasa.
    if (
        stored_draft is None
        and permission_query.intent
        != "ajukan_surat_izin"
    ):
        return None

    if stored_draft is None:
        flow_result = start_permission_conversation(
            conversation_id=conversation_id,
            draft_repository=draft_repository,
        )
    else:
        flow_result = process_permission_draft_input(
            conversation_id=conversation_id,
            message=message,
            draft_repository=draft_repository,
            permission_repository=(
                permission_repository
            ),
        )

    if flow_result.status == "needs_input":
        assert flow_result.draft is not None

        return PermissionChatFlowResult(
            status="needs_clarification",
            message=flow_result.message,
            missing_entities=_missing_entity(
                flow_result.draft.step
            ),
        )

    if flow_result.status == "invalid_input":
        step = (
            flow_result.draft.step
            if flow_result.draft is not None
            else None
        )

        return PermissionChatFlowResult(
            status="invalid_request",
            message=flow_result.message,
            missing_entities=_missing_entity(step),
        )

    if (
        flow_result.status
        == "ready_for_confirmation"
    ):
        return PermissionChatFlowResult(
            status="needs_clarification",
            message=flow_result.message,
            missing_entities=("confirmation",),
        )

    if flow_result.status == "cancelled":
        return PermissionChatFlowResult(
            status="answered",
            message=flow_result.message,
            missing_entities=(),
        )

    if flow_result.status == "expired":
        return PermissionChatFlowResult(
            status="invalid_request",
            message=flow_result.message,
            missing_entities=(),
        )

    if (
        flow_result.status != "confirmed"
        or not flow_result.should_submit
    ):
        raise RuntimeError(
            "Status alur pengajuan tidak dikenal."
        )

    draft = flow_result.draft

    assert draft is not None
    assert draft.student_name is not None
    assert draft.class_name is not None
    assert draft.permission_type is not None
    assert draft.description is not None

    submission_result = submit_permission_request(
        student_name=draft.student_name,
        class_name=draft.class_name,
        permission_type=draft.permission_type,
        description=draft.description,
        phone_number=draft.phone_number,
        repository=permission_repository,
        source_key=(
            f"chat:permission:{conversation_id}"
        ),
    )

    if (
        submission_result.status
        == "configuration_error"
    ):
        return PermissionChatFlowResult(
            status="unavailable",
            message=submission_result.message,
            missing_entities=(),
        )

    if submission_result.status != "created":
        return PermissionChatFlowResult(
            status="invalid_request",
            message=submission_result.message,
            missing_entities=(),
        )

    assert submission_result.request is not None

    # Penghapusan draft masih berada dalam transaksi
    # database chatbot. Jika commit gagal, rollback
    # akan mengembalikan draft untuk percobaan ulang.
    draft_repository.delete(draft)

    return PermissionChatFlowResult(
        status="answered",
        message=build_permission_submission_answer(
            tracking_code=(
                submission_result
                .request
                .tracking_code
            ),
        ),
        missing_entities=(),
        request=submission_result.request,
    )