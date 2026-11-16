import os
from pathlib import Path

from dotenv import load_dotenv


SETTING_NAMES = ("FIREBASE_PROJECT_ID", "FIREBASE_API_KEY", "OLLAMA_BASE_URL")
ENV_PATH = Path(__file__).resolve().with_name(".env")


def load_settings() -> dict[str, str]:
    load_dotenv(ENV_PATH, override=False)
    return {name: os.getenv(name, "").strip() for name in SETTING_NAMES}
