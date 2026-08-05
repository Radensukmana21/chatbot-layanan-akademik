from __future__ import annotations

import logging
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)

from apscheduler.schedulers.background import (
    BackgroundScheduler,
)
from apscheduler.triggers.cron import (
    CronTrigger,
)

from app.core.config import Settings
from app.core.dependencies import (
    get_chatbot_session_factory,
)
from app.services.chatbot_maintenance import (
    run_chatbot_maintenance,
)


logger = logging.getLogger(__name__)

CHATBOT_MAINTENANCE_JOB_ID = (
    "chatbot_database_maintenance"
)


def execute_chatbot_maintenance(
    *,
    batch_size: int,
) -> None:
    """
    Fungsi yang dieksekusi oleh APScheduler.

    Fungsi ini selalu membuat SQLAlchemy Session baru
    melalui session factory. Session request FastAPI
    tidak pernah digunakan oleh background job.
    """

    logger.info(
        "Memulai chatbot maintenance."
    )

    try:
        result = run_chatbot_maintenance(
            session_factory=(
                get_chatbot_session_factory()
            ),
            batch_size=batch_size,
        )
    except Exception:
        logger.exception(
            "Chatbot maintenance gagal."
        )
        raise

    logger.info(
        (
            "Chatbot maintenance selesai: "
            "expired_messages=%s, "
            "redacted_messages=%s, "
            "expired_permission_drafts=%s, "
            "deleted_permission_drafts=%s"
        ),
        result.expired_messages,
        result.redacted_messages,
        result.expired_permission_drafts,
        result.deleted_permission_drafts,
    )


def build_scheduler(
    settings: Settings,
) -> BackgroundScheduler:
    try:
        scheduler_timezone = ZoneInfo(
            settings.scheduler_timezone
        )
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            "Zona waktu scheduler tidak ditemukan: "
            f"{settings.scheduler_timezone!r}."
        ) from exc

    scheduler = BackgroundScheduler(
        timezone=scheduler_timezone,
    )

    scheduler.add_job(
        execute_chatbot_maintenance,
        trigger=CronTrigger(
            hour=(
                settings
                .chatbot_maintenance_hour
            ),
            minute=(
                settings
                .chatbot_maintenance_minute
            ),
            timezone=scheduler_timezone,
        ),
        kwargs={
            "batch_size": (
                settings
                .chatbot_maintenance_batch_size
            ),
        },
        id=CHATBOT_MAINTENANCE_JOB_ID,
        name="Chatbot database maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60 * 60,
    )

    return scheduler


def start_scheduler(
    settings: Settings,
) -> BackgroundScheduler | None:
    if not settings.scheduler_enabled:
        logger.info(
            "APScheduler dinonaktifkan."
        )
        return None

    scheduler = build_scheduler(settings)
    scheduler.start()

    logger.info(
        (
            "APScheduler aktif. "
            "Chatbot maintenance dijadwalkan "
            "pukul %02d:%02d %s."
        ),
        settings.chatbot_maintenance_hour,
        settings.chatbot_maintenance_minute,
        settings.scheduler_timezone,
    )

    return scheduler


def stop_scheduler(
    scheduler: BackgroundScheduler | None,
) -> None:
    if scheduler is None:
        return

    if scheduler.running:
        scheduler.shutdown(
            wait=True
        )

        logger.info(
            "APScheduler dihentikan."
        )