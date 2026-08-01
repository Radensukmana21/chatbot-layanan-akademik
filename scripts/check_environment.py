from __future__ import annotations

import platform
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.database import check_database


def main() -> int:
    settings = get_settings()

    print(f"Python                 : {sys.version.split()[0]}")
    print(f"Operating system       : {platform.platform()}")
    print(f"Application            : {settings.app_name}")
    print(f"Environment            : {settings.app_env}")
    print(f"Port                   : {settings.app_port}")
    print(f"Auto retrain           : {settings.auto_retrain_enabled}")
    print(f"Academic database      : {check_database(settings.academic_database_url)}")
    print(f"Chatbot database       : {check_database(settings.chatbot_database_url)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
