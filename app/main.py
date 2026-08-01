from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import get_settings


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
