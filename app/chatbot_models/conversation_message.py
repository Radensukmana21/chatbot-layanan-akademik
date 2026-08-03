from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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

    # Content berisi hasil kebijakan penyimpanan,
    # bukan selalu teks mentah dari pengguna.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    storage_policy: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="full",
        server_default="full",
        index=True,
    )

    contains_sensitive_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    redacted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
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
        CheckConstraint(
            (
                "storage_policy IN "
                "('full', 'redacted', 'metadata_only')"
            ),
            name="valid_storage_policy",
        ),
        Index(
            "ix_conversation_messages_conversation_order",
            "conversation_id",
            "created_at",
            "id",
        ),
    )