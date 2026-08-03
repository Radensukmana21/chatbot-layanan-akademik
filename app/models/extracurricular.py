from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from app.models.extracurricular_schedule import (
        ExtracurricularSchedule,
    )
    from app.models.teacher import Teacher


class Extracurricular(Base):
    __tablename__ = "extracurriculars"

    __table_args__ = (
        UniqueConstraint(
            "normalized_name",
            name="uq_extracurriculars_normalized_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    advisor_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "teachers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )

    source_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
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

    advisor_teacher: Mapped[Teacher | None] = relationship(
        foreign_keys=[advisor_teacher_id],
    )

    schedules: Mapped[
        list[ExtracurricularSchedule]
    ] = relationship(
        back_populates="extracurricular",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )