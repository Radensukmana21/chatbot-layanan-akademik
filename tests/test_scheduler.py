from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import get_settings
from app.core.scheduler import (
    CHATBOT_MAINTENANCE_JOB_ID,
    build_scheduler,
    start_scheduler,
)


def scheduler_settings():
    return replace(
        get_settings(),
        scheduler_enabled=True,
        scheduler_timezone="Asia/Jakarta",
        chatbot_maintenance_hour=2,
        chatbot_maintenance_minute=0,
        chatbot_maintenance_batch_size=25,
    )


def test_builds_chatbot_maintenance_job(
) -> None:
    scheduler = build_scheduler(
        scheduler_settings()
    )

    scheduler.start(paused=True)

    try:
        job = scheduler.get_job(
            CHATBOT_MAINTENANCE_JOB_ID
        )

        assert job is not None
        assert (
            job.name
            == "Chatbot database maintenance"
        )
        assert job.max_instances == 1
        assert job.coalesce is True
        assert job.kwargs == {
            "batch_size": 25,
        }

        trigger_text = str(job.trigger)

        assert "hour='2'" in trigger_text
        assert "minute='0'" in trigger_text
    finally:
        scheduler.shutdown(
            wait=False
        )


def test_does_not_start_disabled_scheduler(
) -> None:
    settings = replace(
        get_settings(),
        scheduler_enabled=False,
    )

    assert start_scheduler(settings) is None


def test_rejects_unknown_timezone(
) -> None:
    settings = replace(
        scheduler_settings(),
        scheduler_timezone=(
            "Zona/Tidak-Ada"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Zona waktu scheduler",
    ):
        build_scheduler(settings)