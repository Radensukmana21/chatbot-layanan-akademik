from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine


@lru_cache
def get_academic_session_factory() -> sessionmaker[Session]:
    settings = get_settings()

    if not settings.academic_database_url:
        raise RuntimeError(
            "ACADEMIC_DATABASE_URL belum dikonfigurasi."
        )

    engine = build_engine(settings.academic_database_url)

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def get_academic_session() -> Generator[Session, None, None]:
    session_factory = get_academic_session_factory()

    with session_factory() as session:
        yield session