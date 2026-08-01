import pytest

from app.services.class_validator import (
    normalize_class_name,
    validate_class_format,
)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("7A", "7A"),
        ("8 a", "8A"),
        (" 9k ", "9K"),
        ("8J", "8J"),
    ],
)
def test_normalize_class_name(
    raw_value: str,
    expected: str,
) -> None:
    assert normalize_class_name(raw_value) == expected


@pytest.mark.parametrize(
    "class_name",
    [
        "7A",
        "7K",
        "8A",
        "8J",
        "8K",
        "9A",
        "9K",
    ],
)
def test_accepts_valid_class_format(
    class_name: str,
) -> None:
    result = validate_class_format(class_name)

    assert result.is_valid is True
    assert result.class_name == class_name
    assert result.grade in {7, 8, 9}
    assert result.group is not None
    assert result.error_code is None


@pytest.mark.parametrize(
    "class_name",
    [
        "6A",
        "10A",
        "7L",
        "8Z",
        "9AA",
        "A8",
        "VIIA",
        "kelas8A",
    ],
)
def test_rejects_invalid_class_format(
    class_name: str,
) -> None:
    result = validate_class_format(class_name)

    assert result.is_valid is False
    assert result.error_code == "invalid_class_format"


@pytest.mark.parametrize(
    "class_name",
    ["7", "8", "9"],
)
def test_grade_without_group_requires_clarification(
    class_name: str,
) -> None:
    result = validate_class_format(class_name)

    assert result.is_valid is False
    assert result.grade == int(class_name)
    assert result.group is None
    assert result.error_code == "missing_group"


@pytest.mark.parametrize(
    "class_name",
    [None, "", "   "],
)
def test_missing_class(
    class_name: str | None,
) -> None:
    result = validate_class_format(class_name)

    assert result.is_valid is False
    assert result.error_code == "missing_class"


def test_maximum_group_is_k() -> None:
    assert validate_class_format("8K").is_valid is True
    assert validate_class_format("8L").is_valid is False