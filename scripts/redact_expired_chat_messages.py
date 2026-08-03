from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import build_engine
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
    utc_now_naive,
)


def positive_integer(
    value: str,
) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Nilai harus berupa bilangan bulat."
        ) from exc

    if parsed < 1:
        raise argparse.ArgumentTypeError(
            "Nilai harus minimal satu."
        )

    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Menghapus isi pesan chatbot yang sudah "
            "melewati masa retensi."
        )
    )

    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=500,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Hanya menghitung pesan kedaluwarsa "
            "tanpa mengubah database."
        ),
    )

    arguments = parser.parse_args()

    settings = get_settings()

    if not settings.chatbot_database_url:
        print(
            "CHATBOT_DATABASE_URL belum dikonfigurasi.",
            file=sys.stderr,
        )
        return 1

    engine = build_engine(
        settings.chatbot_database_url
    )

    current_time = utc_now_naive()

    try:
        with Session(engine) as session:
            repository = (
                ConversationMessageRepository(
                    session
                )
            )

            expired_count = (
                repository.count_expired_messages(
                    now=current_time
                )
            )

            print(
                f"Pesan kedaluwarsa: {expired_count}"
            )

            if arguments.dry_run:
                print(
                    "Dry run selesai; "
                    "database tidak diubah."
                )
                return 0

            total_redacted = 0

            while True:
                processed = (
                    repository.redact_expired_messages(
                        now=current_time,
                        batch_size=(
                            arguments.batch_size
                        ),
                    )
                )

                if processed == 0:
                    break

                session.commit()
                total_redacted += processed

            print(
                "Pembersihan selesai. "
                f"Pesan disamarkan: {total_redacted}"
            )

            return 0

    except Exception as exc:
        print(
            "Pembersihan gagal: "
            f"{exc.__class__.__name__}",
            file=sys.stderr,
        )
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())