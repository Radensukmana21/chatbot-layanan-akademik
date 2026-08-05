from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
    utc_now_naive,
)
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)


DEFAULT_MAINTENANCE_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class ChatbotMaintenanceResult:
    expired_messages: int
    redacted_messages: int
    expired_permission_drafts: int
    deleted_permission_drafts: int


def run_chatbot_maintenance(
    *,
    session_factory: sessionmaker[Session],
    batch_size: int = DEFAULT_MAINTENANCE_BATCH_SIZE,
    now: datetime | None = None,
) -> ChatbotMaintenanceResult:
    """
    Menjalankan maintenance database chatbot.

    Operasi:
    1. menyamarkan pesan yang melewati masa retensi;
    2. menghapus draft surat izin yang kedaluwarsa.
    """

    if batch_size < 1:
        raise ValueError(
            "batch_size harus minimal satu."
        )

    current_time = now or utc_now_naive()

    with session_factory() as session:
        message_repository = (
            ConversationMessageRepository(
                session
            )
        )

        draft_repository = (
            PermissionDraftRepository(
                session
            )
        )

        expired_messages = (
            message_repository
            .count_expired_messages(
                now=current_time
            )
        )

        expired_permission_drafts = (
            draft_repository.count_expired(
                now=current_time
            )
        )

        total_redacted = 0
        total_deleted = 0

        try:
            while True:
                redacted_count = (
                    message_repository
                    .redact_expired_messages(
                        now=current_time,
                        batch_size=batch_size,
                    )
                )

                deleted_count = (
                    draft_repository.delete_expired(
                        now=current_time,
                        batch_size=batch_size,
                    )
                )

                if (
                    redacted_count == 0
                    and deleted_count == 0
                ):
                    break

                session.commit()

                total_redacted += redacted_count
                total_deleted += deleted_count

        except Exception:
            session.rollback()
            raise

    return ChatbotMaintenanceResult(
        expired_messages=expired_messages,
        redacted_messages=total_redacted,
        expired_permission_drafts=(
            expired_permission_drafts
        ),
        deleted_permission_drafts=(
            total_deleted
        ),
    )