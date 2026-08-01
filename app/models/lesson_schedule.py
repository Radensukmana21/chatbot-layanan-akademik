from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LessonSchedule(Base):
    __tablename__ = "lesson_schedules"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    school_class_id: Mapped[int] = mapped_column(
        ForeignKey(
            "school_classes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "teachers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    day: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )

    # Contoh: legacy:schedules:1
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

    __table_args__ = (
        CheckConstraint(
            (
                "day IN ("
                "'senin', 'selasa', 'rabu', 'kamis', "
                "'jumat', 'sabtu', 'minggu'"
                ")"
            ),
            name="valid_day",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="valid_time_range",
        ),
        Index(
            "ix_lesson_schedules_class_day_time",
            "school_class_id",
            "day",
            "start_time",
        ),
    )