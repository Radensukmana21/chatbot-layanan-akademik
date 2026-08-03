from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.chatbot_models.base import ChatbotBase


class ConversationMessage(ChatbotBase):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    intent: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    intent_source: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    response_status: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    class_name: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    day: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="valid_role",
        ),
        Index(
            "ix_conversation_messages_conversation_order",
            "conversation_id",
            "created_at",
            "id",
        ),
    )