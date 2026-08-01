from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AcademicYear, SchoolClass


class MultipleActiveAcademicYearsError(RuntimeError):
    """Terjadi ketika lebih dari satu tahun ajaran ditandai aktif."""


class SchoolClassRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active_academic_year(self) -> AcademicYear | None:
        """
        Mengambil satu tahun ajaran aktif.

        Sistem menolak konfigurasi apabila terdapat lebih dari satu
        tahun ajaran aktif agar hasil pencarian kelas tidak ambigu.
        """

        statement = (
            select(AcademicYear)
            .where(AcademicYear.is_active.is_(True))
            .order_by(AcademicYear.start_date.desc())
            .limit(2)
        )

        academic_years = list(self._session.scalars(statement))

        if len(academic_years) > 1:
            raise MultipleActiveAcademicYearsError(
                "Terdapat lebih dari satu tahun ajaran aktif."
            )

        return academic_years[0] if academic_years else None

    def find_active_class(
        self,
        *,
        academic_year_id: int,
        class_name: str,
    ) -> SchoolClass | None:
        statement = (
            select(SchoolClass)
            .where(
                SchoolClass.academic_year_id == academic_year_id,
                SchoolClass.class_name == class_name,
                SchoolClass.is_active.is_(True),
            )
            .limit(1)
        )

        return self._session.scalar(statement)

    def list_active_class_names(
        self,
        *,
        academic_year_id: int,
    ) -> list[str]:
        statement = (
            select(SchoolClass.class_name)
            .where(
                SchoolClass.academic_year_id == academic_year_id,
                SchoolClass.is_active.is_(True),
            )
            .order_by(
                SchoolClass.grade,
                SchoolClass.group_letter,
            )
        )

        return list(self._session.scalars(statement))