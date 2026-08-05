from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
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


@pytest.fixture
def engine():
    database_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    ChatbotBase.metadata.create_all(
        database_engine
    )

    try:
        yield database_engine
    finally:
        ChatbotBase.metadata.drop_all(
            database_engine
        )
        database_engine.dispose()


def create_conversation(
    session: Session,
):
    repository = ConversationRepository(
        session
    )

    conversation = repository.create()
    session.flush()

    return conversation


def test_starts_permission_draft(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        conversation = create_conversation(
            session
        )

        draft = PermissionDraftRepository(
            session
        ).start(
            conversation_id=conversation.id,
            now=now,
        )

        assert draft.conversation_id == conversation.id
        assert draft.step == "student_name"
        assert draft.student_name is None
        assert draft.awaiting_confirmation is False
        assert draft.expires_at == (
            now + timedelta(minutes=30)
        )


def test_gets_active_permission_draft(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        conversation = create_conversation(
            session
        )

        repository = PermissionDraftRepository(
            session
        )

        repository.start(
            conversation_id=conversation.id,
            now=now,
        )

        draft = repository.get_active(
            conversation_id=conversation.id,
            now=now + timedelta(minutes=10),
        )

        assert draft is not None
        assert draft.step == "student_name"


def test_removes_expired_draft(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        conversation = create_conversation(
            session
        )

        repository = PermissionDraftRepository(
            session
        )

        repository.start(
            conversation_id=conversation.id,
            now=now,
        )

        draft = repository.get_active(
            conversation_id=conversation.id,
            now=now + timedelta(minutes=31),
        )

        assert draft is None

        stored = session.scalar(
            select(PermissionDraft).where(
                PermissionDraft.conversation_id
                == conversation.id
            )
        )

        assert stored is None


def test_restart_clears_old_values(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        conversation = create_conversation(
            session
        )

        repository = PermissionDraftRepository(
            session
        )

        draft = repository.start(
            conversation_id=conversation.id,
            now=now,
        )

        draft.step = "confirmation"
        draft.student_name = "Siswa Sintetis"
        draft.class_name = "7A"
        draft.permission_type = "sakit"
        draft.description = "Data pengujian."
        draft.phone_number = "081234000000"
        draft.awaiting_confirmation = True

        repository.save(
            draft,
            now=now,
        )

        restarted = repository.start(
            conversation_id=conversation.id,
            now=now + timedelta(minutes=5),
        )

        assert restarted.step == "student_name"
        assert restarted.student_name is None
        assert restarted.class_name is None
        assert restarted.permission_type is None
        assert restarted.description is None
        assert restarted.phone_number is None
        assert restarted.awaiting_confirmation is False


def test_deletes_permission_draft(
    engine,
) -> None:
    with Session(engine) as session:
        conversation = create_conversation(
            session
        )

        repository = PermissionDraftRepository(
            session
        )

        draft = repository.start(
            conversation_id=conversation.id,
        )

        repository.delete(draft)

        assert (
            repository.get_active(
                conversation_id=conversation.id
            )
            is None
        )


def test_deletes_expired_drafts_in_batch(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        repository = PermissionDraftRepository(
            session
        )

        conversations = [
            create_conversation(session)
            for _ in range(3)
        ]

        for conversation in conversations:
            repository.start(
                conversation_id=conversation.id,
                now=now,
                ttl_minutes=1,
            )

        deleted = repository.delete_expired(
            now=now + timedelta(minutes=2),
            batch_size=2,
        )

        assert deleted == 2

        remaining = list(
            session.scalars(
                select(PermissionDraft)
            )
        )

        assert len(remaining) == 1

def test_counts_expired_permission_drafts(
    engine,
) -> None:
    now = datetime(2026, 8, 5, 10, 0)

    with Session(engine) as session:
        repository = PermissionDraftRepository(
            session
        )

        expired_conversations = [
            create_conversation(session)
            for _ in range(2)
        ]

        active_conversation = (
            create_conversation(session)
        )

        for conversation in expired_conversations:
            repository.start(
                conversation_id=conversation.id,
                now=now,
                ttl_minutes=1,
            )

        repository.start(
            conversation_id=(
                active_conversation.id
            ),
            now=now,
            ttl_minutes=60,
        )

        expired_count = (
            repository.count_expired(
                now=(
                    now
                    + timedelta(minutes=2)
                ),
            )
        )

        assert expired_count == 2