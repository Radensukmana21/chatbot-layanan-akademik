from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chatbot_models import ConversationMessage


class ConversationMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_user_message(
        self,
        *,
        conversation_id: str,
        content: str,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=content,
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
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
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