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

    # OAuth de Mercado Libre (ver scripts/ml_oauth_setup.py) — actualmente sin uso:
    # /sites/{site}/search quedó bloqueado para terceros desde abril 2025, así que
    # el descubrimiento de ofertas ahora usa src/ml_scraper.py. Se deja este código
    # y estas variables por si en el futuro se necesita OAuth para otra cosa.
    ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
    ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
    ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN", "")
    GH_PAT_SECRETS = os.getenv("GH_PAT_SECRETS", "")
    GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")  # "owner/repo", lo pone GitHub Actions solo

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
