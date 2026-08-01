from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LessonSchedule, Subject, Teacher


@dataclass(frozen=True, slots=True)
class LessonScheduleRecord:
    start_time: time
    end_time: time
    subject_name: str
    subject_type: str
    teacher_name: str | None


class LessonScheduleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_class_and_day(
        self,
        *,
        school_class_id: int,
        day: str,
    ) -> list[LessonScheduleRecord]:
        statement = (
            select(
                LessonSchedule.start_time,
                LessonSchedule.end_time,
                Subject.name,
                Subject.subject_type,
                Teacher.name,
            )
            .join(
                Subject,
                Subject.id == LessonSchedule.subject_id,
            )
            .outerjoin(
                Teacher,
                Teacher.id == LessonSchedule.teacher_id,
            )
            .where(
                LessonSchedule.school_class_id == school_class_id,
                LessonSchedule.day == day,
                LessonSchedule.is_active.is_(True),
                Subject.is_active.is_(True),
            )
            .order_by(
                LessonSchedule.start_time,
                LessonSchedule.end_time,
                LessonSchedule.id,
            )
        )

        rows = self._session.execute(statement).all()

        return [
            LessonScheduleRecord(
                start_time=row[0],
                end_time=row[1],
                subject_name=row[2],
                subject_type=row[3],
                teacher_name=row[4],
            )
            for row in rows
        ]