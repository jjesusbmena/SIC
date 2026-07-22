import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def load_settings(path: Optional[Path] = None) -> dict:
    path = path or ROOT_DIR / "config" / "settings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Env:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    ML_SITE_ID = os.getenv("ML_SITE_ID", "MLM")
    ML_AFFILIATE_EMAIL = os.getenv("ML_AFFILIATE_EMAIL", "")
    ML_AFFILIATE_PASSWORD = os.getenv("ML_AFFILIATE_PASSWORD", "")
    STORAGE_STATE_PATH = str(ROOT_DIR / "storage_state.json")

    @classmethod
    def validate_for_publishing(cls):
        missing = [
            name
            for name, val in [
                ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
                ("TELEGRAM_CHAT_ID", cls.TELEGRAM_CHAT_ID),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                f"Faltan variables de entorno requeridas: {', '.join(missing)}. "
                "Revisa tu archivo .env (usa .env.example como referencia)."
            )
