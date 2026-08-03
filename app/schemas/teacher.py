from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TeacherInformationResponse(BaseModel):
    id: int
    name: str
    subjects: list[str]
    classes: list[str]


class TeacherSearchResponse(BaseModel):
    search_mode: Literal["name", "subject"]
    query: str
    academic_year: str
    message: str
    items: list[TeacherInformationResponse]