from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.chatbot_models import Conversation
from app.services.chat_service import ChatContext


DEFAULT_CONVERSATION_TTL = timedelta(minutes=30)


def utc_now_naive() -> datetime:
    """
    Menghasilkan waktu UTC tanpa timezone.

    Kolom MySQL DATETIME tidak menyimpan informasi timezone,
    sehingga aplikasi menggunakan UTC secara konsisten.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self) -> Conversation:
        conversation = Conversation(
            is_active=False,
        )

        self._session.add(conversation)
        self._session.flush()

        return conversation

    def get_by_id(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        return self._session.get(
            Conversation,
            conversation_id,
        )

    def load_context(
        self,
        conversation: Conversation,
        *,
        now: datetime | None = None,
    ) -> ChatContext:
        current_time = now or utc_now_naive()

        if (
            conversation.is_active
            and conversation.expires_at is not None
            and conversation.expires_at <= current_time
        ):
            conversation.is_active = False
            conversation.expires_at = None

            return ChatContext()

        if not conversation.is_active:
            return ChatContext()

        # Jangan memasukkan intent asing dari database ke ChatContext.
        if conversation.intent != "jadwal_pelajaran":
            conversation.is_active = False
            conversation.expires_at = None

            return ChatContext()

        return ChatContext(
            intent="jadwal_pelajaran",
            class_name=conversation.class_name,
            day=conversation.day,
            is_active=True,
        )

    def save_context(
        self,
        conversation: Conversation,
        context: ChatContext,
        *,
        now: datetime | None = None,
        ttl: timedelta = DEFAULT_CONVERSATION_TTL,
    ) -> None:
        current_time = now or utc_now_naive()

        conversation.intent = context.intent
        conversation.class_name = context.class_name
        conversation.day = context.day
        conversation.is_active = context.is_active

        if context.is_active:
            conversation.expires_at = current_time + ttl
        else:
            conversation.expires_at = None