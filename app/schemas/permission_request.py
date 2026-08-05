from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PermissionRequestCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    student_name: str = Field(
        min_length=1,
        max_length=255,
    )

    class_name: str = Field(
        min_length=1,
        max_length=10,
    )

    permission_type: str = Field(
        min_length=1,
        max_length=30,
    )

    description: str = Field(
        min_length=1,
        max_length=2000,
    )

    phone_number: str | None = Field(
        default=None,
        max_length=20,
    )


class PermissionRequestCreateResponse(BaseModel):
    tracking_code: str
    status: Literal["pending"]
    submitted_at: datetime
    message: str


class PermissionRequestStatusResponse(BaseModel):
    tracking_code: str

    status: Literal[
        "pending",
        "approved",
        "rejected",
    ]

    submitted_at: datetime
    reviewed_at: datetime | None
    message: str