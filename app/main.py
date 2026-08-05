from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.schedules import router as schedules_router
from app.api.routes.chat import router as chat_router
from app.core.config import get_settings

from app.api.routes.teachers import (
    router as teachers_router,
)

from app.api.routes.extracurriculars import (
    router as extracurriculars_router,
)

from app.api.routes.permission_requests import (
    router as permission_requests_router,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    description=(
        "Fondasi penyempurnaan chatbot layanan akademik. "
        "Belum dinyatakan siap produksi."
    ),
)

app.include_router(chat_router)
app.include_router(schedules_router)
app.include_router(teachers_router)
app.include_router(extracurriculars_router)
app.include_router(permission_requests_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "message": "API aktif. Buka /docs untuk dokumentasi.",
    }
