from typing import Dict, Optional


def load_model_preferences() -> Dict[str, str]:
    """Compatibility shim for old callers.

    The application no longer has a global current model. Search requests select
    a public model profile, and administrators publish model revisions instead.
    """

    return {"current_model_file": "", "default_model_file": ""}


def save_model_preferences(preferences: Dict[str, str]) -> None:
    _ = preferences


def get_current_model_file() -> Optional[str]:
    return None


def set_current_model_file(model_file: str) -> None:
    _ = model_file


def get_default_model_file() -> Optional[str]:
    return None


def set_default_model_file(model_file: str) -> None:
    _ = model_file
