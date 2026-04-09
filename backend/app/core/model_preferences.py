import json
from pathlib import Path

from app.core.config import settings


PREFERENCES_PATH = Path(settings.BASE_DIR).joinpath("app/core/model_preferences.json")


def load_model_preferences() -> dict:
    if not PREFERENCES_PATH.exists():
        return {}

    try:
        with PREFERENCES_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_model_preferences(preferences: dict) -> None:
    PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PREFERENCES_PATH.open("w", encoding="utf-8") as file:
        json.dump(preferences, file, ensure_ascii=False, indent=2)


def get_default_model_file() -> str | None:
    value = load_model_preferences().get("default_model_file")
    return value if isinstance(value, str) and value else None


def set_default_model_file(model_file: str) -> None:
    preferences = load_model_preferences()
    preferences["default_model_file"] = model_file
    save_model_preferences(preferences)
