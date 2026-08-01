from pathlib import Path

import pytest

from scripts.import_legacy_schedule import (
    LegacySqlParseError,
    classify_subject_type,
    load_legacy_data,
    normalize_legacy_day,
    parse_insert_rows,
    parse_values_block,
)


def test_parse_values_handles_commas_null_and_times() -> None:
    values = """
(1, 'Dra. Contoh, M.M', NULL, '06:30:00'),
(2, 'Guru Kedua', 7, '07:10:00')
"""

    rows = parse_values_block(values)

    assert rows == [
        (1, "Dra. Contoh, M.M", None, "06:30:00"),
        (2, "Guru Kedua", 7, "07:10:00"),
    ]


def test_parse_insert_rows_maps_columns() -> None:
    sql = """
INSERT INTO `teachers` (`id`, `nama`) VALUES
    (1, 'Guru Satu'),
    (2, 'Guru Dua');
"""

    rows = parse_insert_rows(sql, "teachers")

    assert rows == [
        {"id": 1, "nama": "Guru Satu"},
        {"id": 2, "nama": "Guru Dua"},
    ]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Matematika", "lesson"),
        ("Prakarya", "lesson"),
        ("Upacara", "activity"),
        ("Literasi", "activity"),
        ("Sholat Duha", "activity"),
        ("Guru Mengaji", "activity"),
        ("Pembiasaan", "activity"),
        ("Istirahat 1", "break"),
        ("Istirahat 2", "break"),
    ],
)
def test_classify_subject_type(
    name: str,
    expected: str,
) -> None:
    assert classify_subject_type(name) == expected


@pytest.mark.parametrize(
    ("raw_day", "expected"),
    [
        ("Senin", "senin"),
        ("Selasa", "selasa"),
        ("Rabu", "rabu"),
        ("Kamis", "kamis"),
        ("Jumat", "jumat"),
    ],
)
def test_normalize_legacy_day(
    raw_day: str,
    expected: str,
) -> None:
    assert normalize_legacy_day(raw_day) == expected


def test_rejects_unknown_day() -> None:
    with pytest.raises(ValueError, match="tidak dikenali"):
        normalize_legacy_day("Hari Raya")


def test_rejects_missing_insert() -> None:
    with pytest.raises(
        LegacySqlParseError,
        match="tidak ditemukan",
    ):
        parse_insert_rows("", "teachers")


def test_load_legacy_data_validates_references(
    tmp_path: Path,
) -> None:
    sql_file = tmp_path / "legacy.sql"
    sql_file.write_text(
        """
INSERT INTO `classrooms` (`id`, `nama_kelas`, `tingkat`, `wali_kelas_id`) VALUES
(1, '7A', '7', 1);

INSERT INTO `teachers` (`id`, `nama`) VALUES
(1, 'Guru Satu');

INSERT INTO `subjects` (`id`, `nama_mapel`) VALUES
(1, 'Matematika');

INSERT INTO `schedules`
(`id`, `classroom_id`, `subject_id`, `teacher_id`, `hari`, `jam_mulai`, `jam_selesai`)
VALUES
(1, 99, 1, 1, 'Senin', '07:00:00', '08:00:00');
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="classroom"):
        load_legacy_data(
            sql_file,
            check_counts=False,
        )
