from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.nlp.normalizers import normalize_text
from app.repositories.extracurricular_repository import (
    ExtracurricularRecord,
    ExtracurricularRepository,
)


ExtracurricularLookupStatus = Literal[
    "ok",
    "invalid_query",
    "not_found",
]


@dataclass(frozen=True, slots=True)
class ExtracurricularLookupResult:
    status: ExtracurricularLookupStatus
    query: str | None
    items: tuple[ExtracurricularRecord, ...]
    message: str


def list_extracurricular_information(
    *,
    repository: ExtracurricularRepository,
) -> ExtracurricularLookupResult:
    items = tuple(repository.list_active())

    if not items:
        return ExtracurricularLookupResult(
            status="not_found",
            query=None,
            items=(),
            message=(
                "Data ekstrakurikuler aktif "
                "belum tersedia."
            ),
        )

    return ExtracurricularLookupResult(
        status="ok",
        query=None,
        items=items,
        message=(
            f"Terdapat {len(items)} "
            "ekstrakurikuler aktif."
        ),
    )


def search_extracurricular_information(
    *,
    query: str,
    repository: ExtracurricularRepository,
) -> ExtracurricularLookupResult:
    normalized_query = normalize_text(query)

    if len(normalized_query) < 2:
        return ExtracurricularLookupResult(
            status="invalid_query",
            query=normalized_query,
            items=(),
            message=(
                "Kata pencarian ekstrakurikuler "
                "minimal dua karakter."
            ),
        )

    items = tuple(
        repository.search_active_by_name(
            normalized_query=normalized_query,
        )
    )

    if not items:
        return ExtracurricularLookupResult(
            status="not_found",
            query=normalized_query,
            items=(),
            message=(
                "Ekstrakurikuler yang dicari "
                "tidak ditemukan."
            ),
        )

    return ExtracurricularLookupResult(
        status="ok",
        query=normalized_query,
        items=items,
        message=(
            f"Ditemukan {len(items)} "
            "ekstrakurikuler yang sesuai."
        ),
    )