from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Paths
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


NEXUS_USERNAME = os.getenv("NEXUS_USERNAME", "").strip()
NEXUS_PASSWORD = os.getenv("NEXUS_PASSWORD", "")

# Playwright
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
# How many users
MAX_CONCURRENT_BROWSERS = int(os.getenv("MAX_CONCURRENT_BROWSERS", "4"))
