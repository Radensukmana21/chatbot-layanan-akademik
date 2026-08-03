from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.extracurricular import Extracurricular


class ExtracurricularSchedule(Base):
    __tablename__ = "extracurricular_schedules"

    __table_args__ = (
        UniqueConstraint(
            "extracurricular_id",
            "day",
            "start_time",
            "end_time",
            name=(
                "uq_extracurricular_schedules_"
                "activity_time"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    extracurricular_id: Mapped[int] = mapped_column(
        ForeignKey(
            "extracurriculars.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    day: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
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

    extracurricular: Mapped[Extracurricular] = relationship(
        back_populates="schedules",
    )