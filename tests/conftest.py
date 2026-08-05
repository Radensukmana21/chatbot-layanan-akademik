from __future__ import annotations

import os


# Mencegah APScheduler menyentuh database development
# ketika FastAPI TestClient menjalankan lifespan.
os.environ["SCHEDULER_ENABLED"] = "false"