from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.school_class import SchoolClass


class PermissionRequest(Base):
    __tablename__ = "permission_requests"

    __table_args__ = (
        UniqueConstraint(
            "tracking_code",
            name="uq_permission_requests_tracking_code",
        ),
        UniqueConstraint(
            "source_key",
            name="uq_permission_requests_source_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    tracking_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    school_class_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "school_classes.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Snapshot nama kelas tetap disimpan agar riwayat
    # surat tidak berubah ketika data kelas diperbarui.
    class_name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    student_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    permission_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Data sensitif. Field ini tidak boleh ditampilkan
    # pada response status atau dicatat ke log.
    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    source_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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

    school_class: Mapped[SchoolClass | None] = relationship(
        foreign_keys=[school_class_id],
    )