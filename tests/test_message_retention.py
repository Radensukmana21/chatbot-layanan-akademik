from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.chatbot_models import ChatbotBase
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.services.message_privacy import (
    RETENTION_EXPIRED_PLACEHOLDER,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
    )

    ChatbotBase.metadata.create_all(engine)

    with Session(engine) as database_session:
        yield database_session

    ChatbotBase.metadata.drop_all(engine)
    engine.dispose()


def test_counts_expired_messages(
    session: Session,
) -> None:
    conversation_repository = (
        ConversationRepository(session)
    )
    message_repository = (
        ConversationMessageRepository(session)
    )

    conversation = (
        conversation_repository.create()
    )

    initial_time = datetime(
        2026,
        8,
        1,
        0,
        0,
        0,
    )

    message_repository.add_user_message(
        conversation_id=conversation.id,
        content="Jadwal kelas 7A",
        retention_days=1,
        now=initial_time,
    )

    count = (
        message_repository.count_expired_messages(
            now=initial_time
            + timedelta(days=2)
        )
    )

    assert count == 1


def test_redacts_expired_message(
    session: Session,
) -> None:
    conversation_repository = (
        ConversationRepository(session)
    )
    message_repository = (
        ConversationMessageRepository(session)
    )

    conversation = (
        conversation_repository.create()
    )

    initial_time = datetime(
        2026,
        8,
        1,
        0,
        0,
        0,
    )

    message = (
        message_repository.add_user_message(
            conversation_id=conversation.id,
            content="Jadwal kelas 7A",
            retention_days=1,
            now=initial_time,
        )
    )

    cleanup_time = (
        initial_time + timedelta(days=2)
    )

    processed = (
        message_repository.redact_expired_messages(
            now=cleanup_time,
        )
    )

    assert processed == 1
    assert (
        message.content
        == RETENTION_EXPIRED_PLACEHOLDER
    )
    assert (
        message.storage_policy
        == "metadata_only"
    )
    assert message.retention_until is None
    assert message.redacted_at == cleanup_time


def test_does_not_redact_unexpired_message(
    session: Session,
) -> None:
    conversation_repository = (
        ConversationRepository(session)
    )
    message_repository = (
        ConversationMessageRepository(session)
    )

    conversation = (
        conversation_repository.create()
    )

    initial_time = datetime(
        2026,
        8,
        1,
        0,
        0,
        0,
    )

    message = (
        message_repository.add_user_message(
            conversation_id=conversation.id,
            content="Jadwal kelas 7A",
            retention_days=30,
            now=initial_time,
        )
    )

    processed = (
        message_repository.redact_expired_messages(
            now=initial_time
            + timedelta(days=1),
        )
    )

    assert processed == 0
    assert message.content == "Jadwal kelas 7A"
    assert message.redacted_at is None


def test_cleanup_is_idempotent(
    session: Session,
) -> None:
    conversation_repository = (
        ConversationRepository(session)
    )
    message_repository = (
        ConversationMessageRepository(session)
    )

    conversation = (
        conversation_repository.create()
    )

    initial_time = datetime(
        2026,
        8,
        1,
        0,
        0,
        0,
    )

    message_repository.add_user_message(
        conversation_id=conversation.id,
        content="Jadwal kelas 7A",
        retention_days=1,
        now=initial_time,
    )

    cleanup_time = (
        initial_time + timedelta(days=2)
    )

    first_processed = (
        message_repository.redact_expired_messages(
            now=cleanup_time,
        )
    )

    second_processed = (
        message_repository.redact_expired_messages(
            now=cleanup_time,
        )
    )

    assert first_processed == 1
    assert second_processed == 0


def test_respects_batch_size(
    session: Session,
) -> None:
    conversation_repository = (
        ConversationRepository(session)
    )
    message_repository = (
        ConversationMessageRepository(session)
    )

    conversation = (
        conversation_repository.create()
    )

    initial_time = datetime(
        2026,
        8,
        1,
        0,
        0,
        0,
    )

    for index in range(3):
        message_repository.add_user_message(
            conversation_id=conversation.id,
            content=f"Pesan {index}",
            retention_days=1,
            now=initial_time,
        )

    processed = (
        message_repository.redact_expired_messages(
            now=initial_time
            + timedelta(days=2),
            batch_size=2,
        )
    )

    assert processed == 2

    remaining = (
        message_repository.count_expired_messages(
            now=initial_time
            + timedelta(days=2)
        )
    )

    assert remaining == 1