from app.models import Base


def test_schedule_tables_are_registered() -> None:
    assert "teachers" in Base.metadata.tables
    assert "subjects" in Base.metadata.tables
    assert "lesson_schedules" in Base.metadata.tables


def test_lesson_schedule_has_expected_columns() -> None:
    table = Base.metadata.tables["lesson_schedules"]

    assert {
        "id",
        "school_class_id",
        "subject_id",
        "teacher_id",
        "day",
        "start_time",
        "end_time",
        "is_active",
        "source_key",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())


def test_lesson_schedule_foreign_keys() -> None:
    table = Base.metadata.tables["lesson_schedules"]

    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in table.foreign_keys
    }

    assert foreign_keys == {
        "school_classes.id",
        "subjects.id",
        "teachers.id",
    }


def test_subject_has_type_column() -> None:
    table = Base.metadata.tables["subjects"]

    assert "subject_type" in table.columns