from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.chatbot_models import (
    ChatbotBase,
    PermissionDraft,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from scripts.cleanup_expired_permission_drafts import (
    cleanup_expired_permission_drafts,
    positive_integer,
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    ChatbotBase.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield factory
    finally:
        ChatbotBase.metadata.drop_all(engine)
        engine.dispose()


def create_conversation_id(
    session: Session,
) -> str:
    conversation = ConversationRepository(
        session
    ).create()

    session.flush()

    return conversation.id


def seed_drafts(
    session_factory,
) -> datetime:
    now = datetime(2026, 8, 5, 10, 0)

    with session_factory() as session:
        repository = PermissionDraftRepository(
            session
        )

        for _ in range(3):
            conversation_id = (
                create_conversation_id(session)
            )

            repository.start(
                conversation_id=conversation_id,
                now=now,
                ttl_minutes=1,
            )

        active_conversation_id = (
            create_conversation_id(session)
        )

        repository.start(
            conversation_id=(
                active_conversation_id
            ),
            now=now,
            ttl_minutes=60,
        )

        session.commit()

    return now


def test_dry_run_does_not_delete_drafts(
    session_factory,
    monkeypatch,
) -> None:
    now = seed_drafts(session_factory)

    monkeypatch.setattr(
        (
            "app.repositories."
            "permission_draft_repository."
            "utc_now_naive"
        ),
        lambda: now + timedelta(minutes=2),
    )

    expired_count = (
        cleanup_expired_permission_drafts(
            session_factory=session_factory,
            batch_size=2,
            dry_run=True,
        )
    )

    assert expired_count == 3

    with session_factory() as session:
        total_count = session.scalar(
            select(func.count())
            .select_from(PermissionDraft)
        )

    assert total_count == 4


def test_deletes_expired_drafts_in_batches(
    session_factory,
    monkeypatch,
) -> None:
    now = seed_drafts(session_factory)

    monkeypatch.setattr(
        (
            "app.repositories."
            "permission_draft_repository."
            "utc_now_naive"
        ),
        lambda: now + timedelta(minutes=2),
    )

    deleted_count = (
        cleanup_expired_permission_drafts(
            session_factory=session_factory,
            batch_size=2,
            dry_run=False,
        )
    )

    assert deleted_count == 3

    with session_factory() as session:
        remaining_drafts = list(
            session.scalars(
                select(PermissionDraft)
            )
        )

    assert len(remaining_drafts) == 1

    assert (
        remaining_drafts[0].expires_at
        > now + timedelta(minutes=2)
    )


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "abc"],
)
def test_rejects_invalid_batch_size(
    value: str,
) -> None:
    with pytest.raises(
        Exception,
    ):
        positive_integer(value)