from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import time
from pathlib import Path
import re
import sys
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import build_engine
from app.models import (
    AcademicYear,
    LessonSchedule,
    SchoolClass,
    Subject,
    Teacher,
)
from app.nlp.normalizers import DAY_ALIASES, normalize_text


LEGACY_SQL_PATH = (
    PROJECT_ROOT
    / "database"
    / "legacy"
    / "databasesekolah.sql"
)

EXPECTED_COUNTS = {
    "classrooms": 32,
    "teachers": 50,
    "subjects": 19,
    "schedules": 975,
}

ACTIVITY_SUBJECTS = {
    "upacara",
    "literasi",
    "sholat duha",
    "guru mengaji",
    "pembiasaan",
}

BREAK_SUBJECTS = {
    "istirahat 1",
    "istirahat 2",
}


@dataclass(frozen=True, slots=True)
class LegacyData:
    classrooms: list[dict[str, Any]]
    teachers: list[dict[str, Any]]
    subjects: list[dict[str, Any]]
    schedules: list[dict[str, Any]]


class LegacySqlParseError(ValueError):
    """SQL lama tidak memiliki format INSERT yang diharapkan."""


def _convert_unquoted_value(raw_value: str) -> Any:
    value = raw_value.strip()

    if value.upper() == "NULL":
        return None

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)

    return value


def _parse_quoted_value(
    text: str,
    start_index: int,
) -> tuple[str, int]:
    result: list[str] = []
    index = start_index + 1

    while index < len(text):
        character = text[index]

        if character == "\\":
            if index + 1 >= len(text):
                raise LegacySqlParseError(
                    "Escape character tidak lengkap pada string SQL."
                )

            escaped = text[index + 1]
            escape_map = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "0": "\0",
            }
            result.append(escape_map.get(escaped, escaped))
            index += 2
            continue

        if character == "'":
            # SQL juga dapat menulis apostrof sebagai dua tanda petik.
            if index + 1 < len(text) and text[index + 1] == "'":
                result.append("'")
                index += 2
                continue

            return "".join(result), index + 1

        result.append(character)
        index += 1

    raise LegacySqlParseError("String SQL tidak ditutup.")


def parse_values_block(values_block: str) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    index = 0
    length = len(values_block)

    while index < length:
        while (
            index < length
            and values_block[index] in {" ", "\t", "\r", "\n", ","}
        ):
            index += 1

        if index >= length:
            break

        if values_block[index] != "(":
            raise LegacySqlParseError(
                f"Karakter '(' diharapkan pada posisi {index}."
            )

        index += 1
        row: list[Any] = []

        while index < length:
            while index < length and values_block[index].isspace():
                index += 1

            if index >= length:
                raise LegacySqlParseError("Tuple SQL tidak selesai.")

            if values_block[index] == "'":
                value, index = _parse_quoted_value(
                    values_block,
                    index,
                )
                row.append(value)
            else:
                value_start = index

                while (
                    index < length
                    and values_block[index] not in {",", ")"}
                ):
                    index += 1

                raw_value = values_block[value_start:index]
                row.append(_convert_unquoted_value(raw_value))

            while index < length and values_block[index].isspace():
                index += 1

            if index >= length:
                raise LegacySqlParseError("Tuple SQL tidak selesai.")

            if values_block[index] == ",":
                index += 1
                continue

            if values_block[index] == ")":
                index += 1
                break

            raise LegacySqlParseError(
                f"Pemisah field tidak valid pada posisi {index}."
            )

        rows.append(tuple(row))

    return rows


def parse_insert_rows(
    sql_text: str,
    table_name: str,
) -> list[dict[str, Any]]:
    pattern = re.compile(
        rf"INSERT\s+INTO\s+`{re.escape(table_name)}`\s*"
        r"\((?P<columns>.*?)\)\s*VALUES\s*"
        r"(?P<values>.*?);",
        flags=re.IGNORECASE | re.DOTALL,
    )

    results: list[dict[str, Any]] = []

    for match in pattern.finditer(sql_text):
        columns = re.findall(
            r"`([^`]+)`",
            match.group("columns"),
        )
        rows = parse_values_block(match.group("values"))

        for row in rows:
            if len(row) != len(columns):
                raise LegacySqlParseError(
                    f"Jumlah nilai tabel {table_name} tidak sesuai "
                    "dengan jumlah kolom."
                )

            results.append(dict(zip(columns, row, strict=True)))

    if not results:
        raise LegacySqlParseError(
            f"INSERT untuk tabel {table_name!r} tidak ditemukan."
        )

    return results


def load_legacy_data(
    sql_path: Path,
    *,
    check_counts: bool = True,
) -> LegacyData:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL lama tidak ditemukan: {sql_path}")

    sql_text = sql_path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    data = LegacyData(
        classrooms=parse_insert_rows(sql_text, "classrooms"),
        teachers=parse_insert_rows(sql_text, "teachers"),
        subjects=parse_insert_rows(sql_text, "subjects"),
        schedules=parse_insert_rows(sql_text, "schedules"),
    )

    if check_counts:
        actual_counts = {
            "classrooms": len(data.classrooms),
            "teachers": len(data.teachers),
            "subjects": len(data.subjects),
            "schedules": len(data.schedules),
        }

        for table_name, expected_count in EXPECTED_COUNTS.items():
            actual_count = actual_counts[table_name]

            if actual_count != expected_count:
                raise ValueError(
                    f"Tabel {table_name} berisi {actual_count} baris; "
                    f"snapshot terverifikasi mengharapkan "
                    f"{expected_count} baris."
                )

    validate_legacy_references(data)
    return data


def validate_legacy_references(data: LegacyData) -> None:
    classroom_ids = {row["id"] for row in data.classrooms}
    teacher_ids = {row["id"] for row in data.teachers}
    subject_ids = {row["id"] for row in data.subjects}

    if len(classroom_ids) != len(data.classrooms):
        raise ValueError("ID classroom pada SQL lama tidak unik.")

    if len(teacher_ids) != len(data.teachers):
        raise ValueError("ID teacher pada SQL lama tidak unik.")

    if len(subject_ids) != len(data.subjects):
        raise ValueError("ID subject pada SQL lama tidak unik.")

    schedule_ids: set[int] = set()

    for row in data.schedules:
        schedule_id = row["id"]

        if schedule_id in schedule_ids:
            raise ValueError(
                f"ID schedule {schedule_id} duplikat."
            )

        schedule_ids.add(schedule_id)

        if row["classroom_id"] not in classroom_ids:
            raise ValueError(
                f"Schedule {schedule_id} merujuk classroom yang "
                "tidak tersedia."
            )

        if row["subject_id"] not in subject_ids:
            raise ValueError(
                f"Schedule {schedule_id} merujuk subject yang "
                "tidak tersedia."
            )

        teacher_id = row["teacher_id"]

        if teacher_id is not None and teacher_id not in teacher_ids:
            raise ValueError(
                f"Schedule {schedule_id} merujuk teacher yang "
                "tidak tersedia."
            )


def classify_subject_type(subject_name: str) -> str:
    normalized = normalize_text(subject_name)

    if normalized in BREAK_SUBJECTS:
        return "break"

    if normalized in ACTIVITY_SUBJECTS:
        return "activity"

    return "lesson"


def normalize_legacy_day(day: str) -> str:
    normalized = normalize_text(day)
    canonical = DAY_ALIASES.get(normalized)

    if canonical is None:
        raise ValueError(f"Nama hari tidak dikenali: {day!r}")

    return canonical


def parse_legacy_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Format waktu tidak valid: {value!r}"
        ) from exc


def get_active_academic_year(
    session: Session,
    *,
    expected_name: str,
) -> AcademicYear:
    academic_years = list(
        session.scalars(
            select(AcademicYear).where(
                AcademicYear.is_active.is_(True)
            )
        )
    )

    if len(academic_years) != 1:
        raise ValueError(
            "Database harus memiliki tepat satu tahun ajaran aktif."
        )

    academic_year = academic_years[0]

    if academic_year.name != expected_name:
        raise ValueError(
            f"Tahun ajaran aktif adalah {academic_year.name}, "
            f"sedangkan importer mengharapkan {expected_name}."
        )

    return academic_year


def _single_or_none(items: Iterable[Any], *, entity: str) -> Any | None:
    values = list(items)

    if len(values) > 1:
        raise ValueError(
            f"Ditemukan lebih dari satu {entity} dengan nama normalisasi "
            "yang sama."
        )

    return values[0] if values else None


def import_legacy_data(
    session: Session,
    data: LegacyData,
    *,
    expected_academic_year: str,
) -> dict[str, int]:
    academic_year = get_active_academic_year(
        session,
        expected_name=expected_academic_year,
    )

    active_classes = list(
        session.scalars(
            select(SchoolClass).where(
                SchoolClass.academic_year_id == academic_year.id,
                SchoolClass.is_active.is_(True),
            )
        )
    )

    classes_by_name = {
        school_class.class_name: school_class
        for school_class in active_classes
    }

    legacy_class_names = {
        str(row["nama_kelas"]).strip().upper()
        for row in data.classrooms
    }

    missing_classes = sorted(
        legacy_class_names - classes_by_name.keys()
    )

    if missing_classes:
        raise ValueError(
            "Kelas berikut belum tersedia pada database aktif: "
            + ", ".join(missing_classes)
        )

    teachers_by_legacy_id: dict[int, Teacher] = {}

    for row in data.teachers:
        display_name = str(row["nama"]).strip()
        normalized_name = normalize_text(display_name)

        teacher = _single_or_none(
            session.scalars(
                select(Teacher).where(
                    Teacher.normalized_name == normalized_name
                )
            ),
            entity="guru",
        )

        if teacher is None:
            teacher = Teacher(
                name=display_name,
                normalized_name=normalized_name,
                is_active=True,
            )
            session.add(teacher)
        else:
            teacher.name = display_name
            teacher.is_active = True

        session.flush()
        teachers_by_legacy_id[int(row["id"])] = teacher

    subjects_by_legacy_id: dict[int, Subject] = {}

    for row in data.subjects:
        display_name = str(row["nama_mapel"]).strip()
        normalized_name = normalize_text(display_name)
        subject_type = classify_subject_type(display_name)

        subject = session.scalar(
            select(Subject).where(
                Subject.normalized_name == normalized_name
            )
        )

        if subject is None:
            subject = Subject(
                name=display_name,
                normalized_name=normalized_name,
                subject_type=subject_type,
                is_active=True,
            )
            session.add(subject)
        else:
            subject.name = display_name
            subject.subject_type = subject_type
            subject.is_active = True

        session.flush()
        subjects_by_legacy_id[int(row["id"])] = subject

    source_prefix = (
        f"legacy:{expected_academic_year}:schedules:"
    )

    session.execute(
        update(LessonSchedule)
        .where(LessonSchedule.source_key.like(f"{source_prefix}%"))
        .values(is_active=False)
    )

    imported_schedule_count = 0

    classrooms_by_legacy_id = {
        int(row["id"]): str(row["nama_kelas"]).strip().upper()
        for row in data.classrooms
    }

    for row in data.schedules:
        legacy_schedule_id = int(row["id"])
        class_name = classrooms_by_legacy_id[
            int(row["classroom_id"])
        ]
        school_class = classes_by_name[class_name]
        subject = subjects_by_legacy_id[int(row["subject_id"])]

        teacher_id = row["teacher_id"]
        teacher = (
            teachers_by_legacy_id[int(teacher_id)]
            if teacher_id is not None
            else None
        )

        source_key = (
            f"{source_prefix}{legacy_schedule_id}"
        )

        schedule = session.scalar(
            select(LessonSchedule).where(
                LessonSchedule.source_key == source_key
            )
        )

        if schedule is None:
            schedule = LessonSchedule(source_key=source_key)
            session.add(schedule)

        schedule.school_class_id = school_class.id
        schedule.subject_id = subject.id
        schedule.teacher_id = teacher.id if teacher else None
        schedule.day = normalize_legacy_day(str(row["hari"]))
        schedule.start_time = parse_legacy_time(
            str(row["jam_mulai"])
        )
        schedule.end_time = parse_legacy_time(
            str(row["jam_selesai"])
        )
        schedule.is_active = True

        imported_schedule_count += 1

    return {
        "classrooms": len(data.classrooms),
        "teachers": len(data.teachers),
        "subjects": len(data.subjects),
        "schedules": imported_schedule_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mengimpor kelas, guru, mata pelajaran, dan jadwal dari "
            "snapshot SQL tugas akhir. Tabel surat_izin tidak dibaca."
        )
    )
    parser.add_argument(
        "--sql",
        type=Path,
        default=LEGACY_SQL_PATH,
    )
    parser.add_argument(
        "--academic-year",
        default="2025/2026",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse dan validasi SQL tanpa menulis database.",
    )
    parser.add_argument(
        "--skip-count-check",
        action="store_true",
        help=(
            "Lewati pemeriksaan jumlah baris snapshot. "
            "Gunakan hanya untuk SQL yang memang sudah berubah."
        ),
    )
    arguments = parser.parse_args()

    try:
        data = load_legacy_data(
            arguments.sql,
            check_counts=not arguments.skip_count_check,
        )
    except (FileNotFoundError, UnicodeError, ValueError) as exc:
        print(f"Validasi SQL gagal: {exc}", file=sys.stderr)
        return 1

    print("SQL lama berhasil diparse dan divalidasi.")
    print(f"Classrooms : {len(data.classrooms)}")
    print(f"Teachers   : {len(data.teachers)}")
    print(f"Subjects   : {len(data.subjects)}")
    print(f"Schedules  : {len(data.schedules)}")
    print("Tabel surat_izin tidak dibaca.")

    if arguments.dry_run:
        print("Dry run selesai; database tidak diubah.")
        return 0

    settings = get_settings()

    if not settings.academic_database_url:
        print(
            "ACADEMIC_DATABASE_URL belum dikonfigurasi.",
            file=sys.stderr,
        )
        return 1

    engine = build_engine(settings.academic_database_url)

    try:
        with Session(engine) as session:
            counts = import_legacy_data(
                session,
                data,
                expected_academic_year=arguments.academic_year,
            )
            session.commit()
    except Exception as exc:
        print(f"Import database gagal: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print("Import database berhasil.")
    print(f"Kelas referensi : {counts['classrooms']}")
    print(f"Guru             : {counts['teachers']}")
    print(f"Subjek/kegiatan  : {counts['subjects']}")
    print(f"Jadwal            : {counts['schedules']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
