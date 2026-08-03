from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import time
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_academic_session_factory,
)
from app.models import (
    Extracurricular,
    ExtracurricularSchedule,
    Teacher,
)
from app.nlp.normalizers import normalize_text
from scripts.import_legacy_schedule import (
    LegacySqlParseError,
    parse_insert_rows,
)


DEFAULT_SQL_PATH = (
    PROJECT_ROOT
    / "database"
    / "legacy"
    / "databasesekolah.sql"
)


@dataclass(frozen=True, slots=True)
class ImportSummary:
    extracurriculars_created: int
    extracurriculars_updated: int
    schedules_created: int
    schedules_updated: int
    advisors_resolved: int
    unresolved_advisor_ids: tuple[int, ...]


def parse_table_rows(
    sql_text: str,
    table_name: str,
) -> list[dict[str, Any]]:
    try:
        return parse_insert_rows(
            sql_text,
            table_name,
        )
    except LegacySqlParseError as exc:
        raise RuntimeError(
            f"Gagal membaca tabel legacy {table_name!r}."
        ) from exc


def require_int(
    row: dict[str, Any],
    key: str,
) -> int:
    value = row.get(key)

    if value is None:
        raise ValueError(
            f"Kolom {key!r} wajib memiliki nilai."
        )

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Nilai kolom {key!r} bukan integer: "
            f"{value!r}"
        ) from exc


def optional_int(
    row: dict[str, Any],
    key: str,
) -> int | None:
    value = row.get(key)

    if value is None or value == "":
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Nilai kolom {key!r} bukan integer: "
            f"{value!r}"
        ) from exc


def optional_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def first_text(
    row: dict[str, Any],
    *keys: str,
) -> str | None:
    for key in keys:
        value = optional_text(row.get(key))

        if value is not None:
            return value

    return None


def parse_clock(
    value: Any,
    *,
    column_name: str,
) -> time:
    if isinstance(value, time):
        return value

    text = optional_text(value)

    if text is None:
        raise ValueError(
            f"Kolom {column_name!r} wajib diisi."
        )

    try:
        return time.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"Format waktu pada kolom "
            f"{column_name!r} tidak valid: {text!r}"
        ) from exc


def build_legacy_teacher_name_map(
    sql_text: str,
) -> dict[int, str]:
    teacher_rows = parse_table_rows(
        sql_text,
        "teachers",
    )

    teacher_names: dict[int, str] = {}

    for row in teacher_rows:
        legacy_teacher_id = require_int(
            row,
            "id",
        )

        teacher_name = first_text(
            row,
            "nama",
            "nama_guru",
            "name",
        )

        if teacher_name is not None:
            teacher_names[
                legacy_teacher_id
            ] = teacher_name

    return teacher_names


def build_current_teacher_map(
    session: Session,
) -> dict[str, int]:
    statement = (
        select(Teacher)
        .where(
            Teacher.is_active.is_(True),
        )
        .order_by(Teacher.id)
    )

    teachers = list(
        session.scalars(statement)
    )

    grouped_ids: dict[str, list[int]] = {}

    for teacher in teachers:
        normalized_name = teacher.normalized_name

        if not normalized_name:
            continue

        grouped_ids.setdefault(
            normalized_name,
            [],
        ).append(teacher.id)

    # Nama yang ambigu tidak digunakan untuk mencegah
    # relasi pembina jatuh ke guru yang salah.
    return {
        normalized_name: teacher_ids[0]
        for normalized_name, teacher_ids
        in grouped_ids.items()
        if len(teacher_ids) == 1
    }


def find_extracurricular(
    session: Session,
    *,
    source_key: str,
    normalized_name: str,
) -> Extracurricular | None:
    by_source = session.scalar(
        select(Extracurricular).where(
            Extracurricular.source_key
            == source_key
        )
    )

    if by_source is not None:
        return by_source

    return session.scalar(
        select(Extracurricular).where(
            Extracurricular.normalized_name
            == normalized_name
        )
    )


def find_extracurricular_schedule(
    session: Session,
    *,
    source_key: str,
    extracurricular_id: int,
    day: str,
    start_time: time,
    end_time: time,
) -> ExtracurricularSchedule | None:
    by_source = session.scalar(
        select(
            ExtracurricularSchedule
        ).where(
            ExtracurricularSchedule.source_key
            == source_key
        )
    )

    if by_source is not None:
        return by_source

    return session.scalar(
        select(
            ExtracurricularSchedule
        ).where(
            ExtracurricularSchedule.extracurricular_id
            == extracurricular_id,
            ExtracurricularSchedule.day
            == day,
            ExtracurricularSchedule.start_time
            == start_time,
            ExtracurricularSchedule.end_time
            == end_time,
        )
    )


def import_legacy_extracurriculars(
    session: Session,
    *,
    sql_text: str,
) -> ImportSummary:
    extracurricular_rows = parse_table_rows(
        sql_text,
        "extracurriculars",
    )

    schedule_rows = parse_table_rows(
        sql_text,
        "extracurricular_schedules",
    )

    legacy_teacher_names = (
        build_legacy_teacher_name_map(
            sql_text
        )
    )

    current_teacher_ids = (
        build_current_teacher_map(
            session
        )
    )

    extracurricular_ids: dict[int, int] = {}

    extracurriculars_created = 0
    extracurriculars_updated = 0
    schedules_created = 0
    schedules_updated = 0
    advisors_resolved = 0

    unresolved_advisor_ids: set[int] = set()

    for row in extracurricular_rows:
        legacy_id = require_int(
            row,
            "id",
        )

        name = first_text(
            row,
            "nama_eksul",
            "nama_ekskul",
            "name",
        )

        if name is None:
            raise ValueError(
                "Nama ekstrakurikuler tidak boleh kosong "
                f"pada legacy id {legacy_id}."
            )

        normalized_name = normalize_text(name)

        if not normalized_name:
            raise ValueError(
                "Nama ekstrakurikuler tidak valid "
                f"pada legacy id {legacy_id}."
            )

        source_key = (
            f"legacy:extracurricular:{legacy_id}"
        )

        extracurricular = find_extracurricular(
            session,
            source_key=source_key,
            normalized_name=normalized_name,
        )

        if extracurricular is None:
            extracurricular = Extracurricular(
                name=name,
                normalized_name=normalized_name,
                is_active=True,
                source_key=source_key,
            )

            session.add(extracurricular)
            extracurriculars_created += 1
        else:
            extracurriculars_updated += 1

        extracurricular.name = name
        extracurricular.normalized_name = (
            normalized_name
        )
        extracurricular.location = optional_text(
            row.get("lokasi")
        )
        extracurricular.description = optional_text(
            row.get("deskripsi")
        )
        extracurricular.is_active = True
        extracurricular.source_key = source_key

        legacy_advisor_id = optional_int(
            row,
            "pembina_id",
        )

        if legacy_advisor_id is not None:
            legacy_advisor_name = (
                legacy_teacher_names.get(
                    legacy_advisor_id
                )
            )

            current_advisor_id: int | None = None

            if legacy_advisor_name is not None:
                current_advisor_id = (
                    current_teacher_ids.get(
                        normalize_text(
                            legacy_advisor_name
                        )
                    )
                )

            if current_advisor_id is not None:
                extracurricular.advisor_teacher_id = (
                    current_advisor_id
                )
                advisors_resolved += 1
            else:
                # Jangan menimpa relasi lama yang mungkin
                # sudah diperbaiki secara manual.
                unresolved_advisor_ids.add(
                    legacy_advisor_id
                )

        session.flush()

        extracurricular_ids[
            legacy_id
        ] = extracurricular.id

    for row in schedule_rows:
        legacy_schedule_id = require_int(
            row,
            "id",
        )

        legacy_extracurricular_id = require_int(
            row,
            "extracurricular_id",
        )

        extracurricular_id = (
            extracurricular_ids.get(
                legacy_extracurricular_id
            )
        )

        if extracurricular_id is None:
            raise ValueError(
                "Jadwal mengacu ke ekstrakurikuler "
                "yang tidak ditemukan: "
                f"{legacy_extracurricular_id}."
            )

        day = normalize_text(
            optional_text(row.get("hari"))
        )

        if not day:
            raise ValueError(
                "Hari jadwal tidak boleh kosong "
                f"pada legacy id "
                f"{legacy_schedule_id}."
            )

        start_time = parse_clock(
            row.get("jam_mulai"),
            column_name="jam_mulai",
        )

        end_time = parse_clock(
            row.get("jam_selesai"),
            column_name="jam_selesai",
        )

        if end_time <= start_time:
            raise ValueError(
                "Jam selesai harus lebih besar "
                "daripada jam mulai pada legacy id "
                f"{legacy_schedule_id}."
            )

        source_key = (
            "legacy:extracurricular_schedule:"
            f"{legacy_schedule_id}"
        )

        schedule = find_extracurricular_schedule(
            session,
            source_key=source_key,
            extracurricular_id=extracurricular_id,
            day=day,
            start_time=start_time,
            end_time=end_time,
        )

        if schedule is None:
            schedule = ExtracurricularSchedule(
                extracurricular_id=(
                    extracurricular_id
                ),
                day=day,
                start_time=start_time,
                end_time=end_time,
                is_active=True,
                source_key=source_key,
            )

            session.add(schedule)
            schedules_created += 1
        else:
            schedules_updated += 1

        schedule.extracurricular_id = (
            extracurricular_id
        )
        schedule.day = day
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.is_active = True
        schedule.source_key = source_key

    session.flush()

    return ImportSummary(
        extracurriculars_created=(
            extracurriculars_created
        ),
        extracurriculars_updated=(
            extracurriculars_updated
        ),
        schedules_created=schedules_created,
        schedules_updated=schedules_updated,
        advisors_resolved=advisors_resolved,
        unresolved_advisor_ids=tuple(
            sorted(unresolved_advisor_ids)
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Impor data ekstrakurikuler dari SQL "
            "legacy ke academic_school."
        )
    )

    parser.add_argument(
        "--sql",
        type=Path,
        default=DEFAULT_SQL_PATH,
        help="Lokasi file SQL legacy.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validasi dan proses data tanpa "
            "menyimpan perubahan."
        ),
    )

    return parser


def print_summary(
    summary: ImportSummary,
    *,
    dry_run: bool,
) -> None:
    print()
    print("Ringkasan impor ekstrakurikuler")
    print("-" * 40)

    print(
        "Ekstrakurikuler dibuat : "
        f"{summary.extracurriculars_created}"
    )
    print(
        "Ekstrakurikuler diperbarui: "
        f"{summary.extracurriculars_updated}"
    )
    print(
        "Jadwal dibuat           : "
        f"{summary.schedules_created}"
    )
    print(
        "Jadwal diperbarui       : "
        f"{summary.schedules_updated}"
    )
    print(
        "Pembina berhasil dipetakan: "
        f"{summary.advisors_resolved}"
    )

    if summary.unresolved_advisor_ids:
        unresolved = ", ".join(
            str(value)
            for value
            in summary.unresolved_advisor_ids
        )

        print(
            "ID pembina belum terpetakan: "
            f"{unresolved}"
        )
    else:
        print(
            "ID pembina belum terpetakan: tidak ada"
        )

    print(
        "Mode                    : "
        + (
            "DRY RUN, perubahan dibatalkan"
            if dry_run
            else "COMMIT"
        )
    )


def main() -> int:
    args = build_parser().parse_args()

    sql_path: Path = args.sql.resolve()

    if not sql_path.exists():
        print(
            f"File SQL tidak ditemukan: {sql_path}",
            file=sys.stderr,
        )
        return 1

    sql_text = sql_path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    session_factory = (
        get_academic_session_factory()
    )

    with session_factory() as session:
        try:
            summary = (
                import_legacy_extracurriculars(
                    session,
                    sql_text=sql_text,
                )
            )

            if args.dry_run:
                session.rollback()
            else:
                session.commit()

        except Exception as exc:
            session.rollback()

            print(
                f"Impor gagal: "
                f"{exc.__class__.__name__}: {exc}",
                file=sys.stderr,
            )

            return 1

    print_summary(
        summary,
        dry_run=args.dry_run,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())