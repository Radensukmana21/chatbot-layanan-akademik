from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import build_engine
from app.models import AcademicYear, SchoolClass
from app.services.class_validator import validate_class_format


SEED_DIRECTORY = PROJECT_ROOT / "database" / "seeds"


@dataclass(frozen=True, slots=True)
class AcademicYearSeed:
    name: str
    start_date: date
    end_date: date
    is_active: bool


@dataclass(frozen=True, slots=True)
class SchoolClassSeed:
    academic_year: str
    class_name: str
    grade: int
    group_letter: str
    is_active: bool


def parse_boolean(value: str, *, row_number: int) -> bool:
    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "aktif"}:
        return True

    if normalized in {"false", "0", "no", "nonaktif"}:
        return False

    raise ValueError(
        f"Baris {row_number}: nilai boolean {value!r} tidak valid."
    )


def require_headers(
    reader: csv.DictReader,
    required_headers: set[str],
    *,
    file_path: Path,
) -> None:
    available_headers = set(reader.fieldnames or [])
    missing_headers = required_headers - available_headers

    if missing_headers:
        missing = ", ".join(sorted(missing_headers))
        raise ValueError(
            f"File {file_path.name} kehilangan kolom: {missing}."
        )


def load_academic_year_seeds(
    file_path: Path,
) -> dict[str, AcademicYearSeed]:
    if not file_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    result: dict[str, AcademicYearSeed] = {}

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        require_headers(
            reader,
            {"name", "start_date", "end_date", "is_active"},
            file_path=file_path,
        )

        for row_number, row in enumerate(reader, start=2):
            name = row["name"].strip()

            if not name:
                raise ValueError(
                    f"Baris {row_number}: nama tahun ajaran kosong."
                )

            if name in result:
                raise ValueError(
                    f"Baris {row_number}: tahun ajaran {name!r} duplikat."
                )

            try:
                start_date = date.fromisoformat(
                    row["start_date"].strip()
                )
                end_date = date.fromisoformat(
                    row["end_date"].strip()
                )
            except ValueError as exc:
                raise ValueError(
                    f"Baris {row_number}: tanggal harus berformat YYYY-MM-DD."
                ) from exc

            if start_date >= end_date:
                raise ValueError(
                    f"Baris {row_number}: start_date harus sebelum end_date."
                )

            result[name] = AcademicYearSeed(
                name=name,
                start_date=start_date,
                end_date=end_date,
                is_active=parse_boolean(
                    row["is_active"],
                    row_number=row_number,
                ),
            )

    if not result:
        raise ValueError("Data tahun ajaran tidak boleh kosong.")

    active_years = [item for item in result.values() if item.is_active]

    if len(active_years) != 1:
        raise ValueError(
            "Harus terdapat tepat satu tahun ajaran aktif pada file seed."
        )

    return result


def load_school_class_seeds(
    file_path: Path,
    academic_years: dict[str, AcademicYearSeed],
) -> list[SchoolClassSeed]:
    if not file_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    result: list[SchoolClassSeed] = []
    seen: set[tuple[str, str]] = set()

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        require_headers(
            reader,
            {"academic_year", "class_name", "is_active"},
            file_path=file_path,
        )

        for row_number, row in enumerate(reader, start=2):
            academic_year = row["academic_year"].strip()
            raw_class_name = row["class_name"].strip()

            if academic_year not in academic_years:
                raise ValueError(
                    f"Baris {row_number}: tahun ajaran "
                    f"{academic_year!r} tidak terdaftar."
                )

            validation = validate_class_format(raw_class_name)

            if (
                not validation.is_valid
                or validation.class_name is None
                or validation.grade is None
                or validation.group is None
            ):
                raise ValueError(
                    f"Baris {row_number}: "
                    f"{validation.message or 'kelas tidak valid.'}"
                )

            key = (academic_year, validation.class_name)

            if key in seen:
                raise ValueError(
                    f"Baris {row_number}: kelas "
                    f"{validation.class_name} duplikat untuk "
                    f"tahun ajaran {academic_year}."
                )

            seen.add(key)

            result.append(
                SchoolClassSeed(
                    academic_year=academic_year,
                    class_name=validation.class_name,
                    grade=validation.grade,
                    group_letter=validation.group,
                    is_active=parse_boolean(
                        row["is_active"],
                        row_number=row_number,
                    ),
                )
            )

    if not result:
        raise ValueError("Daftar kelas tidak boleh kosong.")

    return result


def load_seed_files(
    academic_years_path: Path,
    school_classes_path: Path,
) -> tuple[
    dict[str, AcademicYearSeed],
    list[SchoolClassSeed],
]:
    academic_years = load_academic_year_seeds(academic_years_path)
    school_classes = load_school_class_seeds(
        school_classes_path,
        academic_years,
    )
    return academic_years, school_classes


def apply_seed(
    session: Session,
    academic_year_seeds: dict[str, AcademicYearSeed],
    school_class_seeds: list[SchoolClassSeed],
) -> None:
    # File seed adalah sumber kebenaran untuk tahun ajaran aktif.
    session.execute(
        update(AcademicYear).values(is_active=False)
    )

    academic_year_models: dict[str, AcademicYear] = {}

    for seed in academic_year_seeds.values():
        model = session.scalar(
            select(AcademicYear).where(AcademicYear.name == seed.name)
        )

        if model is None:
            model = AcademicYear(name=seed.name)
            session.add(model)

        model.start_date = seed.start_date
        model.end_date = seed.end_date
        model.is_active = seed.is_active

        session.flush()
        academic_year_models[seed.name] = model

    # Kelas yang pernah ada pada tahun yang sedang di-seed dibuat nonaktif
    # terlebih dahulu. Baris CSV kemudian mengaktifkan kembali kelas resmi.
    for academic_year in academic_year_models.values():
        session.execute(
            update(SchoolClass)
            .where(
                SchoolClass.academic_year_id == academic_year.id
            )
            .values(is_active=False)
        )

    for seed in school_class_seeds:
        academic_year = academic_year_models[seed.academic_year]

        model = session.scalar(
            select(SchoolClass).where(
                SchoolClass.academic_year_id == academic_year.id,
                SchoolClass.class_name == seed.class_name,
            )
        )

        if model is None:
            model = SchoolClass(
                academic_year_id=academic_year.id,
                class_name=seed.class_name,
            )
            session.add(model)

        model.grade = seed.grade
        model.group_letter = seed.group_letter
        model.is_active = seed.is_active


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Memvalidasi dan memuat tahun ajaran serta kelas."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya validasi CSV tanpa menulis ke database.",
    )
    parser.add_argument(
        "--academic-years",
        type=Path,
        default=SEED_DIRECTORY / "academic_years.csv",
    )
    parser.add_argument(
        "--school-classes",
        type=Path,
        default=SEED_DIRECTORY / "school_classes.csv",
    )
    args = parser.parse_args()

    try:
        academic_years, school_classes = load_seed_files(
            args.academic_years,
            args.school_classes,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Validasi seed gagal: {exc}", file=sys.stderr)
        return 1

    active_year = next(
        item for item in academic_years.values() if item.is_active
    )
    active_classes = [
        item
        for item in school_classes
        if item.academic_year == active_year.name and item.is_active
    ]

    print("Validasi seed berhasil.")
    print(f"Tahun ajaran aktif : {active_year.name}")
    print(f"Jumlah kelas aktif : {len(active_classes)}")

    if args.dry_run:
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
            apply_seed(session, academic_years, school_classes)
            session.commit()
    except Exception as exc:
        print(f"Seed database gagal: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print("Data berhasil dimuat ke database academic_school.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
