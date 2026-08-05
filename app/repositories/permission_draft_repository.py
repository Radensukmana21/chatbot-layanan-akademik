from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.chatbot_models import PermissionDraft


DEFAULT_DRAFT_TTL_MINUTES = 30


def utc_now_naive() -> datetime:
    return datetime.now(
        timezone.utc
    ).replace(tzinfo=None)


class PermissionDraftRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_conversation_id(
        self,
        *,
        conversation_id: str,
    ) -> PermissionDraft | None:
        return self._session.get(
            PermissionDraft,
            conversation_id,
        )

    def start(
        self,
        *,
        conversation_id: str,
        now: datetime | None = None,
        ttl_minutes: int = DEFAULT_DRAFT_TTL_MINUTES,
    ) -> PermissionDraft:
        current_time = now or utc_now_naive()

        draft = self._session.get(
            PermissionDraft,
            conversation_id,
        )

        if draft is None:
            draft = PermissionDraft(
                conversation_id=conversation_id,
                step="student_name",
                expires_at=(
                    current_time
                    + timedelta(minutes=ttl_minutes)
                ),
            )
            self._session.add(draft)
        else:
            # Memulai ulang harus membersihkan data lama.
            draft.step = "student_name"
            draft.student_name = None
            draft.class_name = None
            draft.permission_type = None
            draft.description = None
            draft.phone_number = None
            draft.awaiting_confirmation = False
            draft.expires_at = (
                current_time
                + timedelta(minutes=ttl_minutes)
            )

        self._session.flush()

        return draft

    def get_active(
        self,
        *,
        conversation_id: str,
        now: datetime | None = None,
    ) -> PermissionDraft | None:
        current_time = now or utc_now_naive()

        draft = self._session.scalar(
            select(PermissionDraft).where(
                PermissionDraft.conversation_id
                == conversation_id
            )
        )

        if draft is None:
            return None

        if draft.expires_at <= current_time:
            self._session.delete(draft)
            self._session.flush()
            return None

        return draft

    def save(
        self,
        draft: PermissionDraft,
        *,
        now: datetime | None = None,
        ttl_minutes: int = DEFAULT_DRAFT_TTL_MINUTES,
    ) -> PermissionDraft:
        current_time = now or utc_now_naive()

        draft.expires_at = (
            current_time
            + timedelta(minutes=ttl_minutes)
        )

        self._session.add(draft)
        self._session.flush()

        return draft

    def delete(
        self,
        draft: PermissionDraft,
    ) -> None:
        self._session.delete(draft)
        self._session.flush()

    def delete_by_conversation_id(
        self,
        *,
        conversation_id: str,
    ) -> int:
        result = self._session.execute(
            delete(PermissionDraft).where(
                PermissionDraft.conversation_id
                == conversation_id
            )
        )

        self._session.flush()

        return int(result.rowcount or 0)

    def delete_expired(
        self,
        *,
        now: datetime | None = None,
        batch_size: int = 500,
    ) -> int:
        current_time = now or utc_now_naive()

        expired_ids = list(
            self._session.scalars(
                select(
                    PermissionDraft.conversation_id
                )
                .where(
                    PermissionDraft.expires_at
                    <= current_time
                )
                .order_by(
                    PermissionDraft.expires_at
                )
                .limit(batch_size)
            )
        )

        if not expired_ids:
            return 0

        result = self._session.execute(
            delete(PermissionDraft).where(
                PermissionDraft.conversation_id.in_(
                    expired_ids
                )
            )
        )

        self._session.flush()

        return int(result.rowcount or 0)