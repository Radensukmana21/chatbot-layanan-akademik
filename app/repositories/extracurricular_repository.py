from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    joinedload,
    selectinload,
)

from app.models import (
    Extracurricular,
)


DAY_ORDER = {
    "senin": 1,
    "selasa": 2,
    "rabu": 3,
    "kamis": 4,
    "jumat": 5,
    "sabtu": 6,
    "minggu": 7,
}


@dataclass(frozen=True, slots=True)
class ExtracurricularScheduleRecord:
    day: str
    start_time: time
    end_time: time


@dataclass(frozen=True, slots=True)
class ExtracurricularRecord:
    id: int
    name: str
    advisor_name: str | None
    location: str | None
    description: str | None
    schedules: tuple[
        ExtracurricularScheduleRecord,
        ...,
    ]


class ExtracurricularRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(
        self,
    ) -> list[ExtracurricularRecord]:
        statement = (
            select(Extracurricular)
            .options(
                joinedload(
                    Extracurricular.advisor_teacher
                ),
                selectinload(
                    Extracurricular.schedules
                ),
            )
            .where(
                Extracurricular.is_active.is_(True),
            )
            .order_by(Extracurricular.name)
        )

        extracurriculars = list(
            self._session.scalars(statement)
        )

        return [
            self._to_record(extracurricular)
            for extracurricular in extracurriculars
        ]

    def search_active_by_name(
        self,
        *,
        normalized_query: str,
        limit: int = 20,
    ) -> list[ExtracurricularRecord]:
        statement = (
            select(Extracurricular)
            .options(
                joinedload(
                    Extracurricular.advisor_teacher
                ),
                selectinload(
                    Extracurricular.schedules
                ),
            )
            .where(
                Extracurricular.is_active.is_(True),
                Extracurricular.normalized_name.contains(
                    normalized_query
                ),
            )
            .order_by(Extracurricular.name)
            .limit(limit)
        )

        extracurriculars = list(
            self._session.scalars(statement)
        )

        return [
            self._to_record(extracurricular)
            for extracurricular in extracurriculars
        ]

    @staticmethod
    def _to_record(
        extracurricular: Extracurricular,
    ) -> ExtracurricularRecord:
        active_schedules = [
            schedule
            for schedule in extracurricular.schedules
            if schedule.is_active
        ]

        active_schedules.sort(
            key=lambda schedule: (
                DAY_ORDER.get(schedule.day, 99),
                schedule.start_time,
                schedule.end_time,
            )
        )

        schedules = tuple(
            ExtracurricularScheduleRecord(
                day=schedule.day,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
            )
            for schedule in active_schedules
        )

        advisor_name = None

        if extracurricular.advisor_teacher is not None:
            advisor_name = (
                extracurricular.advisor_teacher.name
            )

        return ExtracurricularRecord(
            id=extracurricular.id,
            name=extracurricular.name,
            advisor_name=advisor_name,
            location=extracurricular.location,
            description=extracurricular.description,
            schedules=schedules,
        )