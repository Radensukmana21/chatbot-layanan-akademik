from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime
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
from app.repositories.conversation_message_repository import (  # noqa: E402
    ConversationMessageRepository,
    utc_now_naive,
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
            "Nilai harus minimal satu."
        )

    return parsed_value


def redact_expired_chat_messages(
    *,
    session_factory: sessionmaker[Session],
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    now: datetime | None = None,
) -> tuple[int, int]:
    """
    Menghitung dan menyamarkan pesan kedaluwarsa.

    Return:
        tuple[expired_count, redacted_count]

    Pada dry-run, redacted_count selalu 0.
    """

    if batch_size < 1:
        raise ValueError(
            "batch_size harus minimal satu."
        )

    current_time = now or utc_now_naive()

    with session_factory() as session:
        repository = ConversationMessageRepository(
            session
        )

        expired_count = (
            repository.count_expired_messages(
                now=current_time
            )
        )

        if dry_run:
            return expired_count, 0

        total_redacted = 0

        try:
            while True:
                processed = (
                    repository.redact_expired_messages(
                        now=current_time,
                        batch_size=batch_size,
                    )
                )

                if processed == 0:
                    break

                session.commit()
                total_redacted += processed

                if processed < batch_size:
                    break

        except Exception:
            session.rollback()
            raise

        return expired_count, total_redacted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Menyamarkan isi pesan chatbot yang "
            "sudah melewati masa retensi."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Jumlah maksimum pesan yang diproses "
            "dalam satu transaksi. Default: 500."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Hanya menghitung pesan kedaluwarsa "
            "tanpa mengubah database."
        ),
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        session_factory = (
            get_chatbot_session_factory()
        )

        expired_count, redacted_count = (
            redact_expired_chat_messages(
                session_factory=session_factory,
                batch_size=arguments.batch_size,
                dry_run=arguments.dry_run,
            )
        )

    except Exception as exc:
        print(
            "Pembersihan pesan gagal: "
            f"{exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Pesan kedaluwarsa: {expired_count}"
    )

    if arguments.dry_run:
        print(
            "Dry run selesai; database tidak diubah."
        )
    else:
        print(
            "Pembersihan selesai. "
            f"Pesan disamarkan: {redacted_count}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())