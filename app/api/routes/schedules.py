from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_academic_session
from app.repositories.lesson_schedule_repository import (
    LessonScheduleRepository,
)
from app.repositories.school_class_repository import (
    SchoolClassRepository,
)
from app.schemas.schedule import (
    ClassScheduleResponse,
    ScheduleItemResponse,
)
from app.services.schedule_lookup import lookup_class_schedule


router = APIRouter(
    prefix="/api/v1/classes",
    tags=["class schedules"],
)


@router.get(
    "/{class_name}/schedules/{day}",
    response_model=ClassScheduleResponse,
)
def get_class_schedule(
    class_name: str,
    day: str,
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
) -> ClassScheduleResponse:
    result = lookup_class_schedule(
        class_name=class_name,
        day=day,
        class_repository=SchoolClassRepository(session),
        schedule_repository=LessonScheduleRepository(session),
    )

    if result.status != "ok":
        error_status = {
            "invalid_class": status.HTTP_400_BAD_REQUEST,
            "invalid_day": status.HTTP_400_BAD_REQUEST,
            "class_not_registered": status.HTTP_404_NOT_FOUND,
            "no_active_academic_year": (
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            "configuration_error": (
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
        }[result.status]

        raise HTTPException(
            status_code=error_status,
            detail={
                "code": result.status,
                "message": result.message,
            },
        )

    assert result.class_name is not None
    assert result.day is not None
    assert result.academic_year is not None

    return ClassScheduleResponse(
        academic_year=result.academic_year,
        class_name=result.class_name,
        day=result.day,
        message=result.message,
        items=[
            ScheduleItemResponse.model_validate(item)
            for item in result.items
        ],
    )