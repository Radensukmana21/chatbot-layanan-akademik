from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcademicYear,
    PermissionRequest,
    SchoolClass,
)


class MultipleActiveClassesError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PermissionStatusRecord:
    tracking_code: str
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None


class PermissionRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active_class(
        self,
        *,
        class_name: str,
    ) -> SchoolClass | None:
        statement = (
            select(SchoolClass)
            .join(
                AcademicYear,
                AcademicYear.id
                == SchoolClass.academic_year_id,
            )
            .where(
                AcademicYear.is_active.is_(True),
                SchoolClass.is_active.is_(True),
                SchoolClass.class_name == class_name,
            )
            .order_by(SchoolClass.id)
        )

        classes = list(
            self._session.scalars(statement)
        )

        if len(classes) > 1:
            raise MultipleActiveClassesError(
                "Terdapat lebih dari satu kelas aktif "
                f"dengan nama {class_name!r}."
            )

        if not classes:
            return None

        return classes[0]

    def tracking_code_exists(
        self,
        *,
        tracking_code: str,
    ) -> bool:
        statement = select(
            PermissionRequest.id
        ).where(
            PermissionRequest.tracking_code
            == tracking_code
        )

        return (
            self._session.scalar(statement)
            is not None
        )

    def create(
        self,
        *,
        tracking_code: str,
        school_class_id: int,
        class_name: str,
        student_name: str,
        permission_type: str,
        description: str,
        phone_number: str | None,
    ) -> PermissionRequest:
        request = PermissionRequest(
            tracking_code=tracking_code,
            school_class_id=school_class_id,
            class_name=class_name,
            student_name=student_name,
            permission_type=permission_type,
            description=description,
            phone_number=phone_number,
            status="pending",
        )

        self._session.add(request)
        self._session.flush()
        self._session.refresh(request)

        return request

    def get_status(
        self,
        *,
        tracking_code: str,
    ) -> PermissionStatusRecord | None:
        statement = select(
            PermissionRequest.tracking_code,
            PermissionRequest.status,
            PermissionRequest.submitted_at,
            PermissionRequest.reviewed_at,
        ).where(
            PermissionRequest.tracking_code
            == tracking_code
        )

        row = self._session.execute(
            statement
        ).one_or_none()

        if row is None:
            return None

        return PermissionStatusRecord(
            tracking_code=row.tracking_code,
            status=row.status,
            submitted_at=row.submitted_at,
            reviewed_at=row.reviewed_at,
        )