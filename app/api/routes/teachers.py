from __future__ import annotations

from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_academic_session
from app.repositories.school_class_repository import (
    SchoolClassRepository,
)
from app.repositories.teacher_repository import (
    TeacherRepository,
)
from app.schemas.teacher import (
    TeacherInformationResponse,
    TeacherSearchResponse,
)
from app.services.teacher_lookup import (
    lookup_teacher_information,
)


router = APIRouter(
    prefix="/api/v1/teachers",
    tags=["teachers"],
)


@router.get(
    "/search",
    response_model=TeacherSearchResponse,
)
def search_teachers(
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=100,
        ),
    ],
    search_by: Annotated[
        Literal["name", "subject"],
        Query(alias="by"),
    ] = "name",
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ] = None,
) -> TeacherSearchResponse:
    result = lookup_teacher_information(
        query=q,
        search_mode=search_by,
        class_repository=SchoolClassRepository(
            session
        ),
        teacher_repository=TeacherRepository(
            session
        ),
    )

    if result.status != "ok":
        error_status = {
            "invalid_query": (
                status.HTTP_400_BAD_REQUEST
            ),
            "not_found": status.HTTP_404_NOT_FOUND,
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

    assert result.academic_year is not None

    return TeacherSearchResponse(
        search_mode=result.search_mode,
        query=result.query,
        academic_year=result.academic_year,
        message=result.message,
        items=[
            TeacherInformationResponse(
                id=item.id,
                name=item.name,
                subjects=list(item.subjects),
                classes=list(item.classes),
            )
            for item in result.items
        ],
    )