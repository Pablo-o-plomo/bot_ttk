from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'bot.db'}")

_uploads = os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads"))
_exports = os.getenv("EXPORTS_DIR", str(BASE_DIR / "exports"))

UPLOADS_DIR = Path(_uploads).expanduser().resolve()
EXPORTS_DIR = Path(_exports).expanduser().resolve()
TEMPLATES_DIR = BASE_DIR / "templates"


def ensure_directories() -> None:
    """Create runtime directories if they don't exist."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()
