from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict


class ScheduleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_time: time
    end_time: time
    subject_name: str
    subject_type: str
    teacher_name: str | None


class ClassScheduleResponse(BaseModel):
    academic_year: str
    class_name: str
    day: str
    message: str
    items: list[ScheduleItemResponse]