from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chatbot_models import ConversationMessage
from app.services.message_privacy import (
    StoragePolicy,
    prepare_message_for_storage,
)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

    return current_time + timedelta(days=retention_days)


class ConversationMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_user_message(
        self,
        *,
        conversation_id: str,
        content: str,
        storage_policy: StoragePolicy = "full",
        retention_days: int | None = 30,
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
            retention_until=calculate_retention_until(
                retention_days
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
            retention_until=calculate_retention_until(
                retention_days
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

        return list(self._session.scalars(statement))