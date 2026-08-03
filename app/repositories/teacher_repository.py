from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    LessonSchedule,
    SchoolClass,
    Subject,
    Teacher,
)


@dataclass(frozen=True, slots=True)
class TeacherRecord:
    id: int
    name: str


class TeacherRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search_by_name(
        self,
        *,
        normalized_query: str,
        limit: int = 10,
    ) -> list[TeacherRecord]:
        statement = (
            select(
                Teacher.id,
                Teacher.name,
            )
            .where(
                Teacher.is_active.is_(True),
                Teacher.normalized_name.contains(
                    normalized_query
                ),
            )
            .order_by(Teacher.name)
            .limit(limit)
        )

        rows = self._session.execute(statement).all()

        return [
            TeacherRecord(
                id=row.id,
                name=row.name,
            )
            for row in rows
        ]

    def search_by_subject(
        self,
        *,
        normalized_query: str,
        academic_year_id: int,
        limit: int = 10,
    ) -> list[TeacherRecord]:
        statement = (
            select(
                Teacher.id,
                Teacher.name,
            )
            .join(
                LessonSchedule,
                LessonSchedule.teacher_id == Teacher.id,
            )
            .join(
                Subject,
                Subject.id == LessonSchedule.subject_id,
            )
            .join(
                SchoolClass,
                SchoolClass.id
                == LessonSchedule.school_class_id,
            )
            .where(
                Teacher.is_active.is_(True),
                Subject.is_active.is_(True),
                LessonSchedule.is_active.is_(True),
                SchoolClass.is_active.is_(True),
                SchoolClass.academic_year_id
                == academic_year_id,
                Subject.normalized_name.contains(
                    normalized_query
                ),
            )
            .distinct()
            .order_by(Teacher.name)
            .limit(limit)
        )

        rows = self._session.execute(statement).all()

        return [
            TeacherRecord(
                id=row.id,
                name=row.name,
            )
            for row in rows
        ]

    def list_subject_names(
        self,
        *,
        teacher_id: int,
        academic_year_id: int,
    ) -> list[str]:
        statement = (
            select(Subject.name)
            .join(
                LessonSchedule,
                LessonSchedule.subject_id == Subject.id,
            )
            .join(
                SchoolClass,
                SchoolClass.id
                == LessonSchedule.school_class_id,
            )
            .where(
                LessonSchedule.teacher_id == teacher_id,
                LessonSchedule.is_active.is_(True),
                Subject.is_active.is_(True),
                SchoolClass.is_active.is_(True),
                SchoolClass.academic_year_id
                == academic_year_id,
            )
            .distinct()
            .order_by(Subject.name)
        )

        return list(self._session.scalars(statement))

    def list_class_names(
        self,
        *,
        teacher_id: int,
        academic_year_id: int,
    ) -> list[str]:
        statement = (
            select(
                SchoolClass.class_name,
                SchoolClass.grade,
                SchoolClass.group_letter,
            )
            .join(
                LessonSchedule,
                LessonSchedule.school_class_id
                == SchoolClass.id,
            )
            .where(
                LessonSchedule.teacher_id == teacher_id,
                LessonSchedule.is_active.is_(True),
                SchoolClass.is_active.is_(True),
                SchoolClass.academic_year_id
                == academic_year_id,
            )
            .distinct()
            .order_by(
                SchoolClass.grade,
                SchoolClass.group_letter,
                SchoolClass.class_name,
            )
        )

        rows = self._session.execute(statement).all()

        return [
            row.class_name
            for row in rows
        ]