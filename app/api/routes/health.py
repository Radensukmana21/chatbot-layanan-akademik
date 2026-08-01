from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database
from app.schemas.health import HealthResponse, ReadinessResponse


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    settings = get_settings()

    academic = check_database(settings.academic_database_url)
    chatbot = check_database(settings.chatbot_database_url)

    ready = all(
        check["status"] == "available"
        for check in (academic, chatbot)
    )

    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        academic_database=academic,
        chatbot_database=chatbot,
        auto_retrain_enabled=settings.auto_retrain_enabled,
    )
