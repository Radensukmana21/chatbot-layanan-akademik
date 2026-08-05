from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.core.dependencies import (  # noqa: E402
    get_chatbot_session_factory,
)
from app.repositories.permission_draft_repository import (  # noqa: E402
    PermissionDraftRepository,
)


DEFAULT_BATCH_SIZE = 500


def positive_integer(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Nilai harus berupa bilangan bulat."
        ) from exc

    if parsed_value < 1:
        raise argparse.ArgumentTypeError(
            "Nilai harus minimal 1."
        )

    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Menghapus draft pengajuan surat izin "
            "yang sudah kedaluwarsa dari database "
            "chatbot."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Jumlah maksimum draft yang dihapus "
            "dalam satu transaksi. Default: 500."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Hanya menghitung draft kedaluwarsa "
            "tanpa menghapus data."
        ),
    )

    return parser


def cleanup_expired_permission_drafts(
    *,
    session_factory: sessionmaker[Session],
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> int:
    if batch_size < 1:
        raise ValueError(
            "batch_size harus minimal satu."
        )

    with session_factory() as session:
        repository = PermissionDraftRepository(
            session
        )

        if dry_run:
            return repository.count_expired()

        total_deleted = 0

        try:
            while True:
                deleted_count = (
                    repository.delete_expired(
                        batch_size=batch_size,
                    )
                )

                if deleted_count == 0:
                    break

                session.commit()
                total_deleted += deleted_count

                if deleted_count < batch_size:
                    break

        except Exception:
            session.rollback()
            raise

        return total_deleted


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        session_factory = (
            get_chatbot_session_factory()
        )

        affected_count = (
            cleanup_expired_permission_drafts(
                session_factory=session_factory,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        )

    except Exception as exc:
        print(
            "Gagal membersihkan draft "
            f"kedaluwarsa: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(
            "Dry run selesai. "
            f"Draft kedaluwarsa: {affected_count}"
        )
    else:
        print(
            "Pembersihan selesai. "
            f"Draft dihapus: {affected_count}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())