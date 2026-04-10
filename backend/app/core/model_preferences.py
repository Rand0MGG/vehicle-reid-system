from typing import Dict, Optional

from app.core.system_config import load_system_config, save_system_config


def load_model_preferences() -> Dict[str, str]:
    current_model_file = load_system_config().get("current_model_file", "")
    return {
        "current_model_file": current_model_file,
        "default_model_file": current_model_file,
    }


def save_model_preferences(preferences: Dict[str, str]) -> None:
    current_model_file = ""

    if isinstance(preferences, dict):
        value = preferences.get("current_model_file")
        if not isinstance(value, str) or not value.strip():
            value = preferences.get("default_model_file")
        if isinstance(value, str):
            current_model_file = value.strip()

    save_system_config({"current_model_file": current_model_file})


def get_current_model_file() -> Optional[str]:
    value = load_system_config().get("current_model_file", "")
    return value if isinstance(value, str) and value else None


def set_current_model_file(model_file: str) -> None:
    save_system_config({"current_model_file": model_file})


def get_default_model_file() -> Optional[str]:
    return get_current_model_file()


def set_default_model_file(model_file: str) -> None:
    set_current_model_file(model_file)
