from __future__ import annotations

from datetime import time

from pydantic import BaseModel


class ExtracurricularScheduleResponse(BaseModel):
    day: str
    start_time: time
    end_time: time


class ExtracurricularResponse(BaseModel):
    id: int
    name: str
    advisor_name: str | None
    location: str | None
    description: str | None
    schedules: list[
        ExtracurricularScheduleResponse
    ]


class ExtracurricularCollectionResponse(BaseModel):
    query: str | None = None
    message: str
    items: list[ExtracurricularResponse]