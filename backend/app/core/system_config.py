import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from app.core.config import settings


SYSTEM_CONFIG_PATH = Path(settings.BASE_DIR).joinpath("app/core/system_config.json")
LEGACY_MODEL_PREFERENCES_PATH = Path(settings.BASE_DIR).joinpath("app/core/model_preferences.json")
DEFAULT_ALLOWED_QUERY_SUFFIXES = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

DEFAULT_SYSTEM_CONFIG = {
    "model_device": settings.DEVICE,
    "similarity_threshold": 0.5,
    "max_results": 50,
    "search_default_top_k": 10,
    "gallery_poll_interval_ms": 1500,
    "allowed_query_suffixes": list(DEFAULT_ALLOWED_QUERY_SUFFIXES),
    "log_level": "INFO",
    "current_model_file": "",
    "gallery_model_file": "",
}


def _normalize_model_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _normalize_suffix(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    normalized = value.strip().lower()
    if not normalized:
        return ""

    return normalized if normalized.startswith(".") else f".{normalized}"


def _normalize_suffixes(values: Any) -> list[str]:
    candidates: Iterable[Any]

    if isinstance(values, str):
        candidates = values.split(",")
    elif isinstance(values, list):
        candidates = values
    else:
        candidates = DEFAULT_ALLOWED_QUERY_SUFFIXES

    suffixes = []
    for value in candidates:
        suffix = _normalize_suffix(value)
        if suffix and suffix not in suffixes:
            suffixes.append(suffix)

    return suffixes or list(DEFAULT_ALLOWED_QUERY_SUFFIXES)


def _normalize_system_config(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    normalized = dict(DEFAULT_SYSTEM_CONFIG)

    if not isinstance(data, dict):
        return normalized

    device = data.get("model_device")
    if device in {"cpu", "cuda"}:
        normalized["model_device"] = device

    similarity_threshold = data.get("similarity_threshold")
    if isinstance(similarity_threshold, (int, float)):
        normalized["similarity_threshold"] = float(similarity_threshold)

    max_results = data.get("max_results")
    if isinstance(max_results, (int, float)):
        normalized["max_results"] = max(1, int(max_results))

    search_default_top_k = data.get("search_default_top_k")
    if isinstance(search_default_top_k, (int, float)):
        normalized["search_default_top_k"] = max(1, int(search_default_top_k))

    gallery_poll_interval_ms = data.get("gallery_poll_interval_ms")
    if isinstance(gallery_poll_interval_ms, (int, float)):
        normalized["gallery_poll_interval_ms"] = max(500, int(gallery_poll_interval_ms))

    normalized["allowed_query_suffixes"] = _normalize_suffixes(
        data.get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
    )

    log_level = data.get("log_level")
    if isinstance(log_level, str) and log_level.strip():
        normalized["log_level"] = log_level.strip()

    current_model_file = _normalize_model_name(data.get("current_model_file"))
    if not current_model_file:
        current_model_file = _normalize_model_name(data.get("default_model_file"))
    normalized["current_model_file"] = current_model_file

    normalized["gallery_model_file"] = _normalize_model_name(data.get("gallery_model_file"))
    normalized["search_default_top_k"] = min(
        normalized["search_default_top_k"],
        normalized["max_results"],
    )

    return normalized


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_system_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_system_config(config)
    SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with SYSTEM_CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)

    return normalized


def _migrate_legacy_model_preferences(config: Dict[str, Any]) -> Dict[str, Any]:
    if config.get("current_model_file"):
        return config

    legacy_default_model = _normalize_model_name(
        _read_json_file(LEGACY_MODEL_PREFERENCES_PATH).get("default_model_file")
    )
    if not legacy_default_model:
        return config

    migrated_config = dict(config)
    migrated_config["current_model_file"] = legacy_default_model
    return _write_system_config(migrated_config)


def load_system_config() -> Dict[str, Any]:
    stored_config = _normalize_system_config(_read_json_file(SYSTEM_CONFIG_PATH))
    return _migrate_legacy_model_preferences(stored_config)


def save_system_config(config: Dict[str, Any]) -> Dict[str, Any]:
    merged_config = {**load_system_config(), **(config or {})}
    return _write_system_config(merged_config)


def has_gallery_model_mismatch(config: Optional[Dict[str, Any]] = None) -> bool:
    runtime_config = _normalize_system_config(config or load_system_config())
    current_model_file = runtime_config.get("current_model_file", "")
    gallery_model_file = runtime_config.get("gallery_model_file", "")
    return bool(current_model_file and gallery_model_file and current_model_file != gallery_model_file)
