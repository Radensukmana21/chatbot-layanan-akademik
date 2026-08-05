from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.chatbot_models import (
    ChatbotBase,
    ConversationMessage,
    PermissionDraft,
)
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.permission_draft_repository import (
    PermissionDraftRepository,
)
from scripts.run_chatbot_maintenance import (
    run_chatbot_maintenance,
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


def seed_maintenance_data(
    session_factory,
) -> datetime:
    initial_time = datetime(
        2026,
        8,
        1,
        10,
        0,
    )

    with session_factory() as session:
        expired_conversation_id = (
            create_conversation_id(session)
        )

        active_conversation_id = (
            create_conversation_id(session)
        )

        message_repository = (
            ConversationMessageRepository(
                session
            )
        )

        message_repository.add_user_message(
            conversation_id=(
                expired_conversation_id
            ),
            content="Pesan yang akan kedaluwarsa.",
            retention_days=1,
            now=initial_time,
        )

        message_repository.add_user_message(
            conversation_id=(
                active_conversation_id
            ),
            content="Pesan masih aktif.",
            retention_days=30,
            now=initial_time,
        )

        draft_repository = (
            PermissionDraftRepository(
                session
            )
        )

        draft_repository.start(
            conversation_id=(
                expired_conversation_id
            ),
            now=initial_time,
            ttl_minutes=1,
        )

        draft_repository.start(
            conversation_id=(
                active_conversation_id
            ),
            now=initial_time,
            ttl_minutes=60 * 24 * 30,
        )

        session.commit()

    return initial_time


def test_dry_run_does_not_change_database(
    session_factory,
) -> None:
    initial_time = seed_maintenance_data(
        session_factory
    )

    current_time = (
        initial_time
        + timedelta(days=2)
    )

    result = run_chatbot_maintenance(
        session_factory=session_factory,
        batch_size=1,
        dry_run=True,
        now=current_time,
    )

    assert result.expired_messages == 1
    assert result.redacted_messages == 0
    assert result.expired_drafts == 1
    assert result.deleted_drafts == 0
    assert result.dry_run is True

    with session_factory() as session:
        messages = list(
            session.scalars(
                select(ConversationMessage)
            )
        )

        drafts = list(
            session.scalars(
                select(PermissionDraft)
            )
        )

    assert len(messages) == 2
    assert len(drafts) == 2

    assert all(
        message.redacted_at is None
        for message in messages
    )


def test_runs_all_maintenance_operations(
    session_factory,
) -> None:
    initial_time = seed_maintenance_data(
        session_factory
    )

    current_time = (
        initial_time
        + timedelta(days=2)
    )

    result = run_chatbot_maintenance(
        session_factory=session_factory,
        batch_size=1,
        dry_run=False,
        now=current_time,
    )

    assert result.expired_messages == 1
    assert result.redacted_messages == 1
    assert result.expired_drafts == 1
    assert result.deleted_drafts == 1
    assert result.dry_run is False

    with session_factory() as session:
        messages = list(
            session.scalars(
                select(ConversationMessage)
                .order_by(
                    ConversationMessage.id
                )
            )
        )

        drafts = list(
            session.scalars(
                select(PermissionDraft)
            )
        )

    assert len(messages) == 2
    assert len(drafts) == 1

    redacted_messages = [
        message
        for message in messages
        if message.redacted_at is not None
    ]

    assert len(redacted_messages) == 1

    assert (
        redacted_messages[0].storage_policy
        == "metadata_only"
    )


def test_rejects_invalid_batch_size(
    session_factory,
) -> None:
    with pytest.raises(
        ValueError,
        match="minimal satu",
    ):
        run_chatbot_maintenance(
            session_factory=session_factory,
            batch_size=0,
        )