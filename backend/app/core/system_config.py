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
    "max_deep_thinking_gallery_size": 5000,
    "deep_thinking_candidate_limit_min": 100,
    "deep_thinking_candidate_limit_max": 500,
    "gallery_poll_interval_ms": 1500,
    "allowed_query_suffixes": list(DEFAULT_ALLOWED_QUERY_SUFFIXES),
    "file_browser_roots": [
        str(Path(settings.DATASETS_DIR).resolve()),
        str((Path(settings.BASE_DIR).resolve().parent / "outputs").resolve()),
        str((Path(settings.BASE_DIR).resolve().parent / "configs").resolve()),
    ],
    "log_level": "INFO",
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


def _normalize_path_list(values: Any) -> list[str]:
    candidates: Iterable[Any]
    if isinstance(values, str):
        candidates = values.split(",")
    elif isinstance(values, list):
        candidates = values
    else:
        candidates = DEFAULT_SYSTEM_CONFIG["file_browser_roots"]

    paths = []
    for value in candidates:
        path = str(value or "").strip()
        if path and path not in paths:
            paths.append(path)
    return paths or list(DEFAULT_SYSTEM_CONFIG["file_browser_roots"])


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

    max_deep_thinking_gallery_size = data.get("max_deep_thinking_gallery_size")
    if isinstance(max_deep_thinking_gallery_size, (int, float)):
        normalized["max_deep_thinking_gallery_size"] = max(1, int(max_deep_thinking_gallery_size))

    deep_thinking_candidate_limit_min = data.get("deep_thinking_candidate_limit_min")
    if isinstance(deep_thinking_candidate_limit_min, (int, float)):
        normalized["deep_thinking_candidate_limit_min"] = max(1, int(deep_thinking_candidate_limit_min))

    deep_thinking_candidate_limit_max = data.get("deep_thinking_candidate_limit_max")
    if isinstance(deep_thinking_candidate_limit_max, (int, float)):
        normalized["deep_thinking_candidate_limit_max"] = max(1, int(deep_thinking_candidate_limit_max))

    gallery_poll_interval_ms = data.get("gallery_poll_interval_ms")
    if isinstance(gallery_poll_interval_ms, (int, float)):
        normalized["gallery_poll_interval_ms"] = max(500, int(gallery_poll_interval_ms))

    normalized["allowed_query_suffixes"] = _normalize_suffixes(
        data.get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
    )
    normalized["file_browser_roots"] = _normalize_path_list(data.get("file_browser_roots"))

    log_level = data.get("log_level")
    if isinstance(log_level, str) and log_level.strip():
        normalized["log_level"] = log_level.strip()

    normalized["search_default_top_k"] = min(
        normalized["search_default_top_k"],
        normalized["max_results"],
    )
    normalized["deep_thinking_candidate_limit_max"] = max(
        normalized["deep_thinking_candidate_limit_min"],
        normalized["deep_thinking_candidate_limit_max"],
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
    _ = LEGACY_MODEL_PREFERENCES_PATH
    return config


def load_system_config() -> Dict[str, Any]:
    stored_config = _normalize_system_config(_read_json_file(SYSTEM_CONFIG_PATH))
    return _migrate_legacy_model_preferences(stored_config)


def save_system_config(config: Dict[str, Any]) -> Dict[str, Any]:
    merged_config = {**load_system_config(), **(config or {})}
    return _write_system_config(merged_config)


def has_gallery_model_mismatch(config: Optional[Dict[str, Any]] = None) -> bool:
    _ = config
    return False
