from __future__ import annotations

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


def test_conversation_message_table_is_registered() -> None:
    assert (
        "conversation_messages"
        in ChatbotBase.metadata.tables
    )


def test_saves_user_and_assistant_messages(
    session: Session,
) -> None:
    conversation_repository = ConversationRepository(
        session
    )
    message_repository = ConversationMessageRepository(
        session
    )

    conversation = conversation_repository.create()

    message_repository.add_user_message(
        conversation_id=conversation.id,
        content="Jadwal kelas 7A hari Senin",
    )

    message_repository.add_assistant_message(
        conversation_id=conversation.id,
        content=(
            "Berikut jadwal kelas 7A pada hari Senin."
        ),
        intent="jadwal_pelajaran",
        intent_source="rule",
        response_status="answered",
        class_name="7A",
        day="senin",
    )

    session.commit()

    messages = message_repository.list_for_conversation(
        conversation.id
    )

    assert len(messages) == 2

    assert messages[0].role == "user"
    assert (
        messages[0].content
        == "Jadwal kelas 7A hari Senin"
    )
    assert messages[0].intent is None

    assert messages[1].role == "assistant"
    assert messages[1].intent == "jadwal_pelajaran"
    assert messages[1].intent_source == "rule"
    assert messages[1].response_status == "answered"
    assert messages[1].class_name == "7A"
    assert messages[1].day == "senin"


def test_lists_only_messages_for_requested_conversation(
    session: Session,
) -> None:
    conversation_repository = ConversationRepository(
        session
    )
    message_repository = ConversationMessageRepository(
        session
    )

    first_conversation = conversation_repository.create()
    second_conversation = conversation_repository.create()

    message_repository.add_user_message(
        conversation_id=first_conversation.id,
        content="Jadwal kelas 7A",
    )

    message_repository.add_user_message(
        conversation_id=second_conversation.id,
        content="Jadwal kelas 8A",
    )

    session.commit()

    messages = message_repository.list_for_conversation(
        first_conversation.id
    )

    assert len(messages) == 1
    assert messages[0].content == "Jadwal kelas 7A"