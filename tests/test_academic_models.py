from app.models import Base


def test_academic_tables_are_registered() -> None:
    assert "academic_years" in Base.metadata.tables
    assert "school_classes" in Base.metadata.tables


def test_school_class_has_academic_year_foreign_key() -> None:
    table = Base.metadata.tables["school_classes"]

    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in table.foreign_keys
    }

    assert "academic_years.id" in foreign_keys


def test_school_class_has_expected_columns() -> None:
    table = Base.metadata.tables["school_classes"]

    assert {
        "id",
        "academic_year_id",
        "class_name",
        "grade",
        "group_letter",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())