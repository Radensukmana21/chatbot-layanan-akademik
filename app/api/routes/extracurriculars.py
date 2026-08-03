from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_academic_session
from app.repositories.extracurricular_repository import (
    ExtracurricularRepository,
)
from app.schemas.extracurricular import (
    ExtracurricularCollectionResponse,
    ExtracurricularResponse,
    ExtracurricularScheduleResponse,
)
from app.services.extracurricular_lookup import (
    list_extracurricular_information,
    search_extracurricular_information,
)


router = APIRouter(
    prefix="/api/v1/extracurriculars",
    tags=["extracurriculars"],
)


def build_response(
    *,
    query: str | None,
    message: str,
    items: tuple,
) -> ExtracurricularCollectionResponse:
    return ExtracurricularCollectionResponse(
        query=query,
        message=message,
        items=[
            ExtracurricularResponse(
                id=item.id,
                name=item.name,
                advisor_name=item.advisor_name,
                location=item.location,
                description=item.description,
                schedules=[
                    ExtracurricularScheduleResponse(
                        day=schedule.day,
                        start_time=schedule.start_time,
                        end_time=schedule.end_time,
                    )
                    for schedule in item.schedules
                ],
            )
            for item in items
        ],
    )


@router.get(
    "",
    response_model=ExtracurricularCollectionResponse,
)
def list_extracurriculars(
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
) -> ExtracurricularCollectionResponse:
    result = list_extracurricular_information(
        repository=ExtracurricularRepository(
            session
        ),
    )

    if result.status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": result.status,
                "message": result.message,
            },
        )

    return build_response(
        query=result.query,
        message=result.message,
        items=result.items,
    )


@router.get(
    "/search",
    response_model=ExtracurricularCollectionResponse,
)
def search_extracurriculars(
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=100,
        ),
    ],
) -> ExtracurricularCollectionResponse:
    result = search_extracurricular_information(
        query=q,
        repository=ExtracurricularRepository(
            session
        ),
    )

    if result.status != "ok":
        error_status = {
            "invalid_query": (
                status.HTTP_400_BAD_REQUEST
            ),
            "not_found": status.HTTP_404_NOT_FOUND,
        }[result.status]

        raise HTTPException(
            status_code=error_status,
            detail={
                "code": result.status,
                "message": result.message,
            },
        )

    return build_response(
        query=result.query,
        message=result.message,
        items=result.items,
    )