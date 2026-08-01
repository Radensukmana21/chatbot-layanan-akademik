from pathlib import Path

import pytest

from scripts.seed_academic_structure import load_seed_files


def write_file(path: Path, content: str) -> Path:
    path.write_text(
        content.strip() + "\n",
        encoding="utf-8",
    )
    return path


def test_loads_verified_legacy_class_structure(
    tmp_path: Path,
) -> None:
    years = write_file(
        tmp_path / "academic_years.csv",
        """
name,start_date,end_date,is_active
2025/2026,2025-07-01,2026-06-30,true
""",
    )
    classes = write_file(
        tmp_path / "school_classes.csv",
        """
academic_year,class_name,is_active
2025/2026,7A,true
2025/2026,7K,true
2025/2026,8K,true
2025/2026,9J,true
""",
    )

    academic_years, school_classes = load_seed_files(
        years,
        classes,
    )

    assert academic_years["2025/2026"].is_active is True
    assert [item.class_name for item in school_classes] == [
        "7A",
        "7K",
        "8K",
        "9J",
    ]


def test_rejects_class_above_k(tmp_path: Path) -> None:
    years = write_file(
        tmp_path / "academic_years.csv",
        """
name,start_date,end_date,is_active
2025/2026,2025-07-01,2026-06-30,true
""",
    )
    classes = write_file(
        tmp_path / "school_classes.csv",
        """
academic_year,class_name,is_active
2025/2026,8L,true
""",
    )

    with pytest.raises(ValueError, match="tidak valid"):
        load_seed_files(years, classes)


def test_requires_one_active_year(tmp_path: Path) -> None:
    years = write_file(
        tmp_path / "academic_years.csv",
        """
name,start_date,end_date,is_active
2025/2026,2025-07-01,2026-06-30,false
""",
    )
    classes = write_file(
        tmp_path / "school_classes.csv",
        """
academic_year,class_name,is_active
2025/2026,8A,true
""",
    )

    with pytest.raises(ValueError, match="tepat satu"):
        load_seed_files(years, classes)
