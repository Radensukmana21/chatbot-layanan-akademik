from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_academic_session,
)
from app.repositories.permission_request_repository import (
    PermissionRequestRepository,
)
from app.schemas.permission_request import (
    PermissionRequestCreateRequest,
    PermissionRequestCreateResponse,
    PermissionRequestStatusResponse,
)
from app.services.permission_request_service import (
    lookup_permission_status,
    submit_permission_request,
)


router = APIRouter(
    prefix="/api/v1/permission-requests",
    tags=["permission requests"],
)


@router.post(
    "",
    response_model=PermissionRequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission_request(
    payload: PermissionRequestCreateRequest,
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
) -> PermissionRequestCreateResponse:
    repository = PermissionRequestRepository(
        session
    )

    result = submit_permission_request(
        student_name=payload.student_name,
        class_name=payload.class_name,
        permission_type=payload.permission_type,
        description=payload.description,
        phone_number=payload.phone_number,
        repository=repository,
    )

    if result.status != "created":
        error_status = {
            "invalid_name": (
                status.HTTP_400_BAD_REQUEST
            ),
            "invalid_class": (
                status.HTTP_400_BAD_REQUEST
            ),
            "invalid_permission_type": (
                status.HTTP_400_BAD_REQUEST
            ),
            "invalid_description": (
                status.HTTP_400_BAD_REQUEST
            ),
            "invalid_phone_number": (
                status.HTTP_400_BAD_REQUEST
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

    assert result.request is not None

    try:
        session.commit()
        session.refresh(result.request)
    except Exception:
        session.rollback()
        raise

    return PermissionRequestCreateResponse(
        tracking_code=(
            result.request.tracking_code
        ),
        status="pending",
        submitted_at=(
            result.request.submitted_at
        ),
        message=result.message,
    )


@router.get(
    "/{tracking_code}/status",
    response_model=PermissionRequestStatusResponse,
)
def get_permission_request_status(
    tracking_code: str,
    session: Annotated[
        Session,
        Depends(get_academic_session),
    ],
) -> PermissionRequestStatusResponse:
    result = lookup_permission_status(
        tracking_code=tracking_code,
        repository=PermissionRequestRepository(
            session
        ),
    )

    if result.status != "ok":
        error_status = {
            "invalid_code": (
                status.HTTP_400_BAD_REQUEST
            ),
            "not_found": (
                status.HTTP_404_NOT_FOUND
            ),
        }[result.status]

        raise HTTPException(
            status_code=error_status,
            detail={
                "code": result.status,
                "message": result.message,
            },
        )

    assert result.item is not None

    return PermissionRequestStatusResponse(
        tracking_code=(
            result.item.tracking_code
        ),
        status=result.item.status,
        submitted_at=result.item.submitted_at,
        reviewed_at=result.item.reviewed_at,
        message=result.message,
    )