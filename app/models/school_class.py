from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.academic_year import AcademicYear


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey(
            "academic_years.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    class_name: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    grade: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    group_letter: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
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

    academic_year: Mapped["AcademicYear"] = relationship(
        back_populates="classes",
    )

    __table_args__ = (
        CheckConstraint(
            "grade BETWEEN 7 AND 9",
            name="grade_range",
        ),
        CheckConstraint(
            "group_letter BETWEEN 'A' AND 'K'",
            name="group_letter_range",
        ),
        UniqueConstraint(
            "academic_year_id",
            "class_name",
            name="uq_school_classes_year_class",
        ),
    )