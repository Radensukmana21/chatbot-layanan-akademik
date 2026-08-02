from app.chatbot_models import ChatbotBase
from app.models import Base as AcademicBase


def test_conversation_table_is_registered() -> None:
    assert "conversations" in ChatbotBase.metadata.tables


def test_conversation_has_expected_columns() -> None:
    table = ChatbotBase.metadata.tables["conversations"]

    assert {
        "id",
        "intent",
        "class_name",
        "day",
        "is_active",
        "expires_at",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())


def test_chatbot_metadata_is_separate() -> None:
    assert "conversations" not in AcademicBase.metadata.tables

    assert "academic_years" not in ChatbotBase.metadata.tables
    assert "school_classes" not in ChatbotBase.metadata.tables