import hashlib
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.model_profile import ModelProfile, ModelRevision
from app.models.vehicle import GalleryFeature, GalleryImage


REPO_ROOT = Path(settings.BASE_DIR).resolve().parent
OUTPUTS_DIR = REPO_ROOT / "outputs"
CONFIG_ROOTS = (REPO_ROOT / "configs", REPO_ROOT / "fastreid" / "configs")
MODEL_SIGNATURE_VERSION = "v2"


def normalize_path(value: str) -> str:
    return str(value or "").strip().replace("\\", "/")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _iter_files(root: Path, suffixes: Iterable[str]) -> list[str]:
    if not root.exists():
        return []

    allowed = {suffix.lower() for suffix in suffixes}
    files = []
    for file_path in root.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in allowed:
            files.append(file_path.relative_to(root).as_posix())
    return files


def list_weight_files() -> list[str]:
    return sorted(set(_iter_files(OUTPUTS_DIR, {".pth", ".pt"})))


def list_config_files() -> list[str]:
    files = []
    for root in CONFIG_ROOTS:
        for file_path in _iter_files(root, {".yml", ".yaml"}):
            files.append((root / file_path).resolve().relative_to(REPO_ROOT).as_posix())
    return sorted(set(files))


def resolve_weights_file(weights_file: str) -> Path:
    normalized = normalize_path(weights_file).lstrip("/")
    if not normalized:
        raise ValueError("请选择模型权重文件。")

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = OUTPUTS_DIR / normalized

    resolved = candidate.resolve()
    if not _is_relative_to(resolved, OUTPUTS_DIR.resolve()):
        raise ValueError("模型权重文件必须位于 outputs 目录内。")
    return resolved


def resolve_config_file(config_file: str) -> Path:
    normalized = normalize_path(config_file).lstrip("/")
    if not normalized:
        raise ValueError("请选择推理配置文件。")

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / normalized

    resolved = candidate.resolve()
    allowed_roots = [root.resolve() for root in CONFIG_ROOTS]
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise ValueError("推理配置文件必须位于 configs 或 fastreid/configs 目录内。")
    return resolved


def normalize_weights_file(weights_file: str) -> str:
    return resolve_weights_file(weights_file).relative_to(OUTPUTS_DIR.resolve()).as_posix()


def normalize_config_file(config_file: str) -> str:
    return resolve_config_file(config_file).relative_to(REPO_ROOT).as_posix()


def _file_fingerprint(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def compute_revision_signature(revision_like: Any) -> str:
    try:
        weights_path = resolve_weights_file(getattr(revision_like, "weights_file", ""))
        weights_fingerprint = _file_fingerprint(weights_path)
        weights_value = normalize_weights_file(str(getattr(revision_like, "weights_file", "")))
    except ValueError:
        weights_fingerprint = "invalid"
        weights_value = normalize_path(str(getattr(revision_like, "weights_file", "")))

    try:
        config_path = resolve_config_file(getattr(revision_like, "config_file", ""))
        config_fingerprint = _file_fingerprint(config_path)
        config_value = normalize_config_file(str(getattr(revision_like, "config_file", "")))
    except ValueError:
        config_fingerprint = "invalid"
        config_value = normalize_path(str(getattr(revision_like, "config_file", "")))

    payload = "|".join(
        [
            MODEL_SIGNATURE_VERSION,
            weights_value,
            weights_fingerprint,
            config_value,
            config_fingerprint,
            str(int(bool(getattr(revision_like, "supports_concat", False)))),
            str(int(bool(getattr(revision_like, "supports_rerank", True)))),
            str(int(getattr(revision_like, "global_feature_dim", 2048) or 2048)),
            str(int(getattr(revision_like, "full_feature_dim", 2048) or 2048)),
            str(getattr(revision_like, "fast_inference_mode", "global") or "global"),
            str(getattr(revision_like, "pro_inference_mode", "global_detail") or "global_detail"),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_model_signature(profile_or_revision: Any) -> str:
    revision = getattr(profile_or_revision, "active_revision", None) or profile_or_revision
    return getattr(revision, "signature", None) or compute_revision_signature(revision)


def validate_revision_files(revision_like: Any, *, require_exists: bool = False) -> None:
    weights_path = resolve_weights_file(getattr(revision_like, "weights_file", ""))
    config_path = resolve_config_file(getattr(revision_like, "config_file", ""))
    if require_exists and not weights_path.exists():
        raise ValueError(f"模型权重文件不存在：{getattr(revision_like, 'weights_file', '')}")
    if require_exists and not config_path.exists():
        raise ValueError(f"推理配置文件不存在：{getattr(revision_like, 'config_file', '')}")


def normalize_revision_payload(data: dict[str, Any]) -> dict[str, Any]:
    supports_concat = bool(data.get("supports_concat", False))
    global_dim = int(data.get("global_feature_dim") or 2048)
    full_dim = int(data.get("full_feature_dim") or global_dim)
    if global_dim <= 0:
        raise ValueError("全局特征维度必须大于 0。")
    if full_dim < global_dim:
        raise ValueError("完整特征维度不能小于全局特征维度。")
    if not supports_concat:
        full_dim = global_dim

    fast_mode = str(data.get("fast_inference_mode") or "global").strip() or "global"
    pro_mode = str(data.get("pro_inference_mode") or ("global_detail" if supports_concat else fast_mode)).strip()
    if not supports_concat:
        pro_mode = fast_mode

    normalized = {
        "revision_name": str(data.get("revision_name") or "Initial revision").strip() or "Initial revision",
        "weights_file": normalize_weights_file(str(data.get("weights_file") or "")),
        "config_file": normalize_config_file(str(data.get("config_file") or "")),
        "supports_concat": supports_concat,
        "supports_rerank": bool(data.get("supports_rerank", True)),
        "global_feature_dim": global_dim,
        "full_feature_dim": full_dim,
        "fast_inference_mode": fast_mode,
        "pro_inference_mode": pro_mode,
    }
    validate_revision_files(type("RevisionCandidate", (), normalized), require_exists=False)
    normalized["signature"] = compute_revision_signature(type("RevisionCandidate", (), normalized))
    return normalized


def get_profile_or_404(db: Session, profile_id: int) -> Optional[ModelProfile]:
    return (
        db.query(ModelProfile)
        .options(joinedload(ModelProfile.revisions))
        .filter(ModelProfile.id == profile_id)
        .first()
    )


def get_active_revision(profile: ModelProfile) -> Optional[ModelRevision]:
    if not profile:
        return None
    return profile.active_revision


def get_public_profiles(db: Session) -> list[ModelProfile]:
    return (
        db.query(ModelProfile)
        .options(joinedload(ModelProfile.revisions))
        .filter(ModelProfile.is_enabled.is_(True), ModelProfile.is_public.is_(True))
        .order_by(ModelProfile.display_order.asc(), ModelProfile.id.asc())
        .all()
    )


def serialize_revision(revision: Optional[ModelRevision]) -> Optional[dict[str, Any]]:
    if revision is None:
        return None
    return {
        "id": revision.id,
        "model_profile_id": revision.model_profile_id,
        "revision_name": revision.revision_name,
        "weights_file": revision.weights_file,
        "config_file": revision.config_file,
        "supports_concat": bool(revision.supports_concat),
        "supports_rerank": bool(revision.supports_rerank),
        "global_feature_dim": int(revision.global_feature_dim or 0),
        "full_feature_dim": int(revision.full_feature_dim or 0),
        "fast_inference_mode": revision.fast_inference_mode or "global",
        "pro_inference_mode": revision.pro_inference_mode or "global_detail",
        "signature": revision.signature,
        "created_at": revision.created_at,
    }


def serialize_profile(profile: Optional[ModelProfile], *, include_revisions: bool = False) -> Optional[dict[str, Any]]:
    if profile is None:
        return None

    revision = get_active_revision(profile)
    data = {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description or "",
        "is_enabled": bool(profile.is_enabled),
        "is_active": bool(profile.is_enabled),
        "is_public": bool(profile.is_public),
        "display_order": int(profile.display_order or 0),
        "active_revision_id": profile.active_revision_id,
        "active_revision": serialize_revision(revision),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }

    if revision is not None:
        revision_data = serialize_revision(revision) or {}
        data.update(
            {
                "weights_file": revision_data["weights_file"],
                "config_file": revision_data["config_file"],
                "supports_concat": revision_data["supports_concat"],
                "supports_rerank": revision_data["supports_rerank"],
                "global_feature_dim": revision_data["global_feature_dim"],
                "full_feature_dim": revision_data["full_feature_dim"],
                "fast_inference_mode": revision_data["fast_inference_mode"],
                "pro_inference_mode": revision_data["pro_inference_mode"],
                "model_signature": revision_data["signature"],
            }
        )
    else:
        data.update(
            {
                "weights_file": "",
                "config_file": "",
                "supports_concat": False,
                "supports_rerank": False,
                "global_feature_dim": 0,
                "full_feature_dim": 0,
                "fast_inference_mode": "global",
                "pro_inference_mode": "global",
                "model_signature": "",
            }
        )

    if include_revisions:
        data["revisions"] = [serialize_revision(item) for item in sorted(profile.revisions, key=lambda item: item.id)]
    return data


def create_profile_with_revision(db: Session, profile_data: dict[str, Any], revision_data: dict[str, Any]) -> ModelProfile:
    profile = ModelProfile(
        name=str(profile_data.get("name") or "").strip(),
        description=str(profile_data.get("description") or "").strip(),
        is_enabled=bool(profile_data.get("is_enabled", True)),
        is_public=bool(profile_data.get("is_public", True)),
        display_order=int(profile_data.get("display_order") or 0),
    )
    db.add(profile)
    db.flush()

    revision = ModelRevision(model_profile_id=profile.id, **revision_data)
    db.add(revision)
    db.flush()
    profile.active_revision_id = revision.id
    db.commit()
    db.refresh(profile)
    return profile


def create_revision_for_profile(db: Session, profile: ModelProfile, revision_data: dict[str, Any]) -> ModelRevision:
    existing = db.query(ModelRevision).filter(ModelRevision.signature == revision_data["signature"]).first()
    if existing and existing.model_profile_id == profile.id:
        profile.active_revision_id = existing.id
        db.flush()
        return existing

    revision = ModelRevision(model_profile_id=profile.id, **revision_data)
    db.add(revision)
    db.flush()
    profile.active_revision_id = revision.id
    return revision


def get_feature_status(db: Session, revision: ModelRevision) -> dict[str, Any]:
    image_count = db.query(func.count(GalleryImage.id)).scalar() or 0
    feature_count = (
        db.query(func.count(GalleryFeature.id))
        .filter(GalleryFeature.model_revision_id == revision.id)
        .scalar()
        or 0
    )
    return {
        "image_count": int(image_count),
        "feature_count": int(feature_count),
        "missing_count": max(0, int(image_count) - int(feature_count)),
        "is_complete": int(image_count) > 0 and int(feature_count) >= int(image_count),
    }


def gallery_references_profile(db: Session, profile_id: int) -> bool:
    return (
        db.query(func.count(GalleryFeature.id))
        .join(ModelRevision, GalleryFeature.model_revision_id == ModelRevision.id)
        .filter(ModelRevision.model_profile_id == profile_id)
        .scalar()
        or 0
    ) > 0
