from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.chatbot_models import ChatbotBase
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.services.chat_service import ChatContext


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


def test_saves_and_loads_active_context(
    session: Session,
) -> None:
    repository = ConversationRepository(session)
    conversation = repository.create()

    current_time = datetime(2026, 8, 2, 1, 0, 0)

    repository.save_context(
        conversation,
        ChatContext(
            intent="jadwal_pelajaran",
            class_name="7A",
            day="senin",
            is_active=True,
        ),
        now=current_time,
    )

    context = repository.load_context(
        conversation,
        now=current_time + timedelta(minutes=5),
    )

    assert context == ChatContext(
        intent="jadwal_pelajaran",
        class_name="7A",
        day="senin",
        is_active=True,
    )

    assert conversation.expires_at == (
        current_time + timedelta(minutes=30)
    )


def test_returns_empty_context_when_completed(
    session: Session,
) -> None:
    repository = ConversationRepository(session)
    conversation = repository.create()

    repository.save_context(
        conversation,
        ChatContext(
            intent="jadwal_pelajaran",
            class_name="7A",
            day="senin",
            is_active=False,
        ),
    )

    context = repository.load_context(conversation)

    assert context == ChatContext()
    assert conversation.is_active is False
    assert conversation.expires_at is None


def test_closes_expired_context(
    session: Session,
) -> None:
    repository = ConversationRepository(session)
    conversation = repository.create()

    initial_time = datetime(2026, 8, 2, 1, 0, 0)

    repository.save_context(
        conversation,
        ChatContext(
            intent="jadwal_pelajaran",
            class_name="7",
            day=None,
            is_active=True,
        ),
        now=initial_time,
        ttl=timedelta(minutes=30),
    )

    context = repository.load_context(
        conversation,
        now=initial_time + timedelta(minutes=31),
    )

    assert context == ChatContext()
    assert conversation.is_active is False
    assert conversation.expires_at is None


def test_gets_conversation_by_id(
    session: Session,
) -> None:
    repository = ConversationRepository(session)
    conversation = repository.create()

    session.commit()

    result = repository.get_by_id(conversation.id)

    assert result is not None
    assert result.id == conversation.id