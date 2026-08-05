from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.chatbot_models.base import ChatbotBase


class PermissionDraft(ChatbotBase):
    __tablename__ = "permission_drafts"

    __table_args__ = (
        CheckConstraint(
            "step IN ("
            "'student_name', "
            "'class_name', "
            "'permission_type', "
            "'description', "
            "'phone_number', "
            "'confirmation'"
            ")",
            name="ck_permission_drafts_step",
        ),
    )

    # Satu conversation hanya boleh memiliki satu draft.
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    step: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="student_name",
        server_default="student_name",
        index=True,
    )

    # Field berikut berisi data sementara dan sensitif.
    # Jangan menulis nilainya ke log aplikasi.
    student_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    class_name: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    permission_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    awaiting_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )