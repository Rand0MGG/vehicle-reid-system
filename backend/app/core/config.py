import json
import os
from pathlib import Path
from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"


def _load_local_env() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key:
            os.environ.setdefault(key, value)


_load_local_env()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", enable_decoding=False)

    PROJECT_NAME: str = "Vehicle ReID System"
    API_V1_STR: str = "/api/v1"

    BASE_DIR: str = str(BACKEND_DIR)
    DATASETS_DIR: str = str(REPO_ROOT / "datasets")
    GALLERY_DIR: str = str(REPO_ROOT / "datasets" / "gallery")
    MODEL_CONFIG_FILE: str = str(REPO_ROOT / "configs" / "veri_r50ibn_sbs_s0_v1.yml")
    MODEL_WEIGHTS_FILE: str = str(REPO_ROOT / "outputs" / "model_final.pth")
    SEARCH_UPLOAD_DIR: str = str(REPO_ROOT / "tmp" / "search_uploads")

    DEVICE: str = "cpu"

    JWT_SECRET_KEY: str
    SQLALCHEMY_DATABASE_URI: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized.lower().startswith("replace-"):
            raise ValueError("JWT_SECRET_KEY must be set to a real secret")
        return normalized

    @field_validator("SQLALCHEMY_DATABASE_URI")
    @classmethod
    def validate_database_uri(cls, value: str) -> str:
        normalized = value.strip()
        lowered = normalized.lower()
        if not normalized or "replace-" in lowered or "your_password" in lowered:
            raise ValueError("SQLALCHEMY_DATABASE_URI must be set to a real database URI")
        return normalized

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> List[str]:
        if isinstance(value, list):
            return value

        if not isinstance(value, str):
            return ["http://localhost:5173"]

        normalized = value.strip()
        if not normalized:
            return []

        if normalized.startswith("["):
            parsed = json.loads(normalized)
            if not isinstance(parsed, list):
                raise ValueError("ALLOWED_ORIGINS must be a list or comma-separated string")
            origins = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            origins = [item.strip() for item in normalized.split(",") if item.strip()]

        if any(origin == "*" for origin in origins):
            raise ValueError("ALLOWED_ORIGINS must not contain '*' when credentials are enabled")

        return origins


settings = Settings()
