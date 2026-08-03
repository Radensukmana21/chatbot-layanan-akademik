from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chatbot_models import ConversationMessage
from app.services.message_privacy import (
    RETENTION_EXPIRED_PLACEHOLDER,
    StoragePolicy,
    prepare_message_for_storage,
)


def utc_now_naive() -> datetime:
    """
    Menghasilkan waktu UTC tanpa timezone.

    MySQL DATETIME tidak menyimpan informasi timezone,
    sehingga aplikasi menggunakan UTC secara konsisten.
    """

    return datetime.now(
        timezone.utc
    ).replace(tzinfo=None)


def calculate_retention_until(
    retention_days: int | None,
    *,
    now: datetime | None = None,
) -> datetime | None:
    if retention_days is None:
        return None

    if retention_days < 1:
        raise ValueError(
            "retention_days harus minimal satu hari."
        )

    current_time = now or utc_now_naive()

    return current_time + timedelta(
        days=retention_days
    )


class ConversationMessageRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add_user_message(
        self,
        *,
        conversation_id: str,
        content: str,
        storage_policy: StoragePolicy = "full",
        retention_days: int | None = 30,
        now: datetime | None = None,
    ) -> ConversationMessage:
        prepared = prepare_message_for_storage(
            content,
            storage_policy=storage_policy,
        )

        message = ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=prepared.content,
            storage_policy=prepared.storage_policy,
            contains_sensitive_data=(
                prepared.contains_sensitive_data
            ),
            retention_until=(
                calculate_retention_until(
                    retention_days,
                    now=now,
                )
            ),
        )

        self._session.add(message)
        self._session.flush()

        return message

    def add_assistant_message(
        self,
        *,
        conversation_id: str,
        content: str,
        intent: str | None,
        intent_source: str | None,
        response_status: str,
        class_name: str | None,
        day: str | None,
        storage_policy: StoragePolicy = "full",
        retention_days: int | None = 30,
        now: datetime | None = None,
    ) -> ConversationMessage:
        prepared = prepare_message_for_storage(
            content,
            storage_policy=storage_policy,
        )

        message = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=prepared.content,
            storage_policy=prepared.storage_policy,
            contains_sensitive_data=(
                prepared.contains_sensitive_data
            ),
            retention_until=(
                calculate_retention_until(
                    retention_days,
                    now=now,
                )
            ),
            intent=intent,
            intent_source=intent_source,
            response_status=response_status,
            class_name=class_name,
            day=day,
        )

        self._session.add(message)
        self._session.flush()

        return message

    def list_for_conversation(
        self,
        conversation_id: str,
    ) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id
                == conversation_id
            )
            .order_by(
                ConversationMessage.created_at,
                ConversationMessage.id,
            )
        )

        return list(
            self._session.scalars(statement)
        )

    def count_expired_messages(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        current_time = now or utc_now_naive()

        statement = (
            select(func.count())
            .select_from(ConversationMessage)
            .where(
                ConversationMessage.retention_until
                .is_not(None),
                ConversationMessage.retention_until
                <= current_time,
                ConversationMessage.redacted_at
                .is_(None),
            )
        )

        return int(
            self._session.scalar(statement) or 0
        )

    def redact_expired_messages(
        self,
        *,
        now: datetime | None = None,
        batch_size: int = 500,
    ) -> int:
        """
        Menghapus isi pesan yang sudah melewati masa retensi.

        Metadata seperti intent, response_status, class_name,
        dan day tetap disimpan untuk kebutuhan evaluasi.
        """

        if batch_size < 1:
            raise ValueError(
                "batch_size harus minimal satu."
            )

        current_time = now or utc_now_naive()

        statement = (
            select(ConversationMessage)
            .where(
                ConversationMessage.retention_until
                .is_not(None),
                ConversationMessage.retention_until
                <= current_time,
                ConversationMessage.redacted_at
                .is_(None),
            )
            .order_by(ConversationMessage.id)
            .limit(batch_size)
        )

        messages = list(
            self._session.scalars(statement)
        )

        for message in messages:
            message.content = (
                RETENTION_EXPIRED_PLACEHOLDER
            )
            message.storage_policy = "metadata_only"
            message.retention_until = None
            message.redacted_at = current_time

        self._session.flush()

        return len(messages)