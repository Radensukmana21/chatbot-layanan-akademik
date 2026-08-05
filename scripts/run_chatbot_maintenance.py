from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
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
    utc_now_naive,
)
from scripts.cleanup_expired_permission_drafts import (  # noqa: E402
    cleanup_expired_permission_drafts,
)
from scripts.redact_expired_chat_messages import (  # noqa: E402
    redact_expired_chat_messages,
)


DEFAULT_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class ChatbotMaintenanceResult:
    expired_messages: int
    redacted_messages: int
    expired_drafts: int
    deleted_drafts: int
    dry_run: bool


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


def run_chatbot_maintenance(
    *,
    session_factory: sessionmaker[Session],
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    now: datetime | None = None,
) -> ChatbotMaintenanceResult:
    if batch_size < 1:
        raise ValueError(
            "batch_size harus minimal satu."
        )

    current_time = now or utc_now_naive()

    expired_messages, redacted_messages = (
        redact_expired_chat_messages(
            session_factory=session_factory,
            batch_size=batch_size,
            dry_run=dry_run,
            now=current_time,
        )
    )

    # Hitung dengan waktu yang sama agar laporan konsisten.
    expired_drafts = (
        cleanup_expired_permission_drafts(
            session_factory=session_factory,
            batch_size=batch_size,
            dry_run=True,
            now=current_time,
        )
    )

    if dry_run:
        deleted_drafts = 0
    else:
        deleted_drafts = (
            cleanup_expired_permission_drafts(
                session_factory=session_factory,
                batch_size=batch_size,
                dry_run=False,
                now=current_time,
            )
        )

    return ChatbotMaintenanceResult(
        expired_messages=expired_messages,
        redacted_messages=redacted_messages,
        expired_drafts=expired_drafts,
        deleted_drafts=deleted_drafts,
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Menjalankan maintenance database chatbot: "
            "redaksi pesan kedaluwarsa dan penghapusan "
            "draft surat izin kedaluwarsa."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Jumlah maksimum data yang diproses "
            "per transaksi. Default: 500."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Hanya menghitung data kedaluwarsa "
            "tanpa mengubah database."
        ),
    )

    return parser


def print_result(
    result: ChatbotMaintenanceResult,
) -> None:
    mode = (
        "DRY RUN"
        if result.dry_run
        else "EXECUTION"
    )

    print(
        f"Chatbot maintenance mode: {mode}"
    )
    print(
        "Pesan kedaluwarsa: "
        f"{result.expired_messages}"
    )
    print(
        "Pesan disamarkan: "
        f"{result.redacted_messages}"
    )
    print(
        "Draft kedaluwarsa: "
        f"{result.expired_drafts}"
    )
    print(
        "Draft dihapus: "
        f"{result.deleted_drafts}"
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        result = run_chatbot_maintenance(
            session_factory=(
                get_chatbot_session_factory()
            ),
            batch_size=arguments.batch_size,
            dry_run=arguments.dry_run,
        )

    except Exception as exc:
        print(
            "Chatbot maintenance gagal: "
            f"{exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())