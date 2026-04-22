import logging
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.endpoints.auth import get_current_user, require_admin_user
from app.api.response_utils import success_response
from app.core.audit_logger import get_audit_logger
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.security import get_password_hash
from app.core.system_config import DEFAULT_ALLOWED_QUERY_SUFFIXES, load_system_config, save_system_config
from app.db.session import get_db
from app.engine.predictor import reid_engine
from app.models.model_profile import ModelProfile, ModelRevision
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.models.vehicle import GalleryFeature, GalleryImage, VehicleIdentity
from app.schemas.audit_schema import AuditLogResponse
from app.services.gallery_service import (
    clear_features_for_revision,
    create_build_task,
    delete_gallery_image,
    get_revision_feature_status,
    list_gallery_images,
    run_feature_build_task,
    run_register_files_task,
    run_register_folder_task,
    start_gallery_operation,
    sync_status,
)
from app.services.model_profile_service import (
    CONFIG_ROOTS,
    OUTPUTS_DIR,
    REPO_ROOT,
    create_profile_with_revision,
    create_revision_for_profile,
    gallery_references_profile,
    get_active_revision,
    get_feature_status,
    get_profile_or_404,
    list_config_files,
    list_weight_files,
    normalize_revision_payload,
    serialize_profile,
    validate_revision_files,
)


router = APIRouter()
logger = logging.getLogger(__name__)


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


class ConfigUpdate(BaseModel):
    model_device: str
    similarity_threshold: float
    max_results: int
    search_default_top_k: int
    max_deep_thinking_gallery_size: int = 5000
    gallery_poll_interval_ms: int = 1500
    allowed_query_suffixes: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_QUERY_SUFFIXES))
    file_browser_roots: list[str] = Field(default_factory=list)
    log_level: str = "INFO"


class ModelProfilePayload(BaseModel):
    name: str
    description: Optional[str] = ""
    is_enabled: bool = True
    is_active: Optional[bool] = None
    is_public: bool = True
    display_order: int = 0
    revision_name: Optional[str] = "Initial revision"
    weights_file: str
    config_file: str
    supports_concat: bool = False
    supports_rerank: bool = True
    global_feature_dim: int = 2048
    full_feature_dim: int = 2048
    fast_inference_mode: str = "global"
    pro_inference_mode: str = "global_detail"


class ModelProfilePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    display_order: Optional[int] = None
    revision_name: Optional[str] = None
    weights_file: Optional[str] = None
    config_file: Optional[str] = None
    supports_concat: Optional[bool] = None
    supports_rerank: Optional[bool] = None
    global_feature_dim: Optional[int] = None
    full_feature_dim: Optional[int] = None
    fast_inference_mode: Optional[str] = None
    pro_inference_mode: Optional[str] = None


class PublishPayload(BaseModel):
    is_public: bool = True


class FeatureBuildPayload(BaseModel):
    rebuild: bool = False


class RegisterFilesPayload(BaseModel):
    paths: list[str]


class RegisterFolderPayload(BaseModel):
    folder_path: str
    recursive: bool = True


def _success(data=None, message: str = "success"):
    return success_response(data=data, message=message)


def _format_datetime(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "暂无记录"


def _audit(audit_logger: Callable[[Optional[int], str, bool], None], user_id: Optional[int], operation: str, ok: bool) -> None:
    audit_logger(user_id=user_id, operation=operation, status=ok)


def _ensure_valid_role(role: str) -> str:
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in {"admin", "user"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号角色只能是 admin 或 user。")
    return normalized_role


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_builtin": bool(user.is_builtin),
        "create_time": user.create_time,
    }


def _revision_source(profile: ModelProfile, patch: ModelProfilePatch) -> dict:
    revision = get_active_revision(profile)
    if not revision:
        base = {}
    else:
        base = {
            "revision_name": revision.revision_name,
            "weights_file": revision.weights_file,
            "config_file": revision.config_file,
            "supports_concat": revision.supports_concat,
            "supports_rerank": revision.supports_rerank,
            "global_feature_dim": revision.global_feature_dim,
            "full_feature_dim": revision.full_feature_dim,
            "fast_inference_mode": revision.fast_inference_mode,
            "pro_inference_mode": revision.pro_inference_mode,
        }
    for key, value in patch.model_dump(exclude_unset=True).items():
        if key in base or key in {"revision_name", "weights_file", "config_file", "supports_concat", "supports_rerank", "global_feature_dim", "full_feature_dim", "fast_inference_mode", "pro_inference_mode"}:
            base[key] = value
    return base


def _profile_fields_from_payload(payload: ModelProfilePayload | ModelProfilePatch, existing: Optional[ModelProfile] = None) -> dict:
    source = payload.model_dump(exclude_unset=True)
    if "is_active" in source and "is_enabled" not in source:
        source["is_enabled"] = source["is_active"]

    data = {}
    for key in ("name", "description", "is_enabled", "is_public", "display_order"):
        if key in source:
            data[key] = source[key]

    if existing is None or "name" in data:
        name = str(data.get("name", getattr(existing, "name", "")) or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型名称不能为空。")
        data["name"] = name

    if "description" in data:
        data["description"] = str(data["description"] or "").strip()
    if "display_order" in data:
        data["display_order"] = int(data["display_order"] or 0)
    return data


def _validate_profile_name(db: Session, name: str, *, exclude_id: Optional[int] = None) -> None:
    query = db.query(ModelProfile).filter(ModelProfile.name == name)
    if exclude_id:
        query = query.filter(ModelProfile.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="模型档案名称已存在。")


def _serialize_profile_with_status(db: Session, profile: ModelProfile) -> dict:
    data = serialize_profile(profile, include_revisions=True) or {}
    revision = get_active_revision(profile)
    if revision:
        data["feature_status"] = get_revision_feature_status(db, revision)
    else:
        data["feature_status"] = {"image_count": 0, "feature_count": 0, "missing_count": 0, "is_complete": False, "latest_task": None}
    return data


def _serialize_model_state(db: Session) -> dict:
    config = load_system_config()
    profiles = (
        db.query(ModelProfile)
        .options(joinedload(ModelProfile.revisions))
        .order_by(ModelProfile.display_order.asc(), ModelProfile.id.asc())
        .all()
    )
    image_count = db.query(func.count(GalleryImage.id)).scalar() or 0
    feature_count = db.query(func.count(GalleryFeature.id)).scalar() or 0
    return {
        "model_profiles": [_serialize_profile_with_status(db, profile) for profile in profiles],
        "available_model_profiles": [serialize_profile(profile) for profile in profiles if profile.is_enabled],
        "public_model_profiles": [serialize_profile(profile) for profile in profiles if profile.is_enabled and profile.is_public],
        "available_models": list_weight_files(),
        "available_model_count": len(list_weight_files()),
        "available_configs": list_config_files(),
        "available_config_count": len(list_config_files()),
        "gallery_image_count": int(image_count),
        "gallery_feature_count": int(feature_count),
        "initialized": reid_engine.initialized,
        "model_device": reid_engine.device_name,
        "max_results": int(config.get("max_results", 50)),
        "search_default_top_k": int(config.get("search_default_top_k", 10)),
        "max_deep_thinking_gallery_size": int(config.get("max_deep_thinking_gallery_size", 5000)),
        "allowed_query_suffixes": config.get("allowed_query_suffixes", list(DEFAULT_ALLOWED_QUERY_SUFFIXES)),
    }


def _serialize_config() -> dict:
    config = load_system_config()
    return {
        "model_device": reid_engine.device_name,
        "similarity_threshold": float(config.get("similarity_threshold", 0.5)),
        "max_results": int(config.get("max_results", 50)),
        "search_default_top_k": int(config.get("search_default_top_k", 10)),
        "max_deep_thinking_gallery_size": int(config.get("max_deep_thinking_gallery_size", 5000)),
        "gallery_poll_interval_ms": int(config.get("gallery_poll_interval_ms", 1500)),
        "allowed_query_suffixes": config.get("allowed_query_suffixes", list(DEFAULT_ALLOWED_QUERY_SUFFIXES)),
        "file_browser_roots": config.get("file_browser_roots", []),
        "log_level": config.get("log_level", "INFO"),
        "search_upload_dir": str(Path(settings.SEARCH_UPLOAD_DIR).resolve()),
    }


def _serialize_overview(db: Session) -> dict:
    latest_image_time = db.query(func.max(GalleryImage.created_at)).scalar()
    latest_log_time = db.query(func.max(SysLog.exec_time)).scalar()
    total_images = db.query(func.count(GalleryImage.id)).scalar() or 0
    total_features = db.query(func.count(GalleryFeature.id)).scalar() or 0
    total_vehicles = db.query(func.count(VehicleIdentity.id)).scalar() or 0
    profiles = (
        db.query(ModelProfile)
        .options(joinedload(ModelProfile.revisions))
        .order_by(ModelProfile.display_order.asc(), ModelProfile.id.asc())
        .all()
    )
    model_cards = [_serialize_profile_with_status(db, profile) for profile in profiles]
    return {
        "total_images": int(total_images),
        "total_features": int(total_features),
        "total_vehicles": int(total_vehicles),
        "latest_ingestion_time": _format_datetime(latest_image_time),
        "available_model_profile_count": len(profiles),
        "public_model_profile_count": len([item for item in profiles if item.is_public and item.is_enabled]),
        "model_device": reid_engine.device_name,
        "initialized": reid_engine.initialized,
        "gallery_task_running": bool(sync_status["is_running"]),
        "gallery_task_state": "running" if sync_status["is_running"] else "idle",
        "total_users": db.query(User).count(),
        "total_logs": db.query(SysLog).count(),
        "latest_log_time": _format_datetime(latest_log_time),
        "search_upload_dir": str(Path(settings.SEARCH_UPLOAD_DIR).resolve()),
        "model_profiles": model_cards,
    }


def _resolve_browser_roots(kind: str) -> list[Path]:
    kind = (kind or "image").lower()
    if kind == "weights":
        return [OUTPUTS_DIR.resolve()]
    if kind == "config":
        return [root.resolve() for root in CONFIG_ROOTS]

    roots = [Path(item).expanduser().resolve() for item in load_system_config().get("file_browser_roots", [])]
    roots.append(Path(settings.DATASETS_DIR).resolve())
    return sorted({root for root in roots if root.exists()})


def _safe_browser_path(path_value: Optional[str], roots: list[Path]) -> Path:
    if not roots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可浏览的根目录。")
    if not path_value:
        return roots[0]
    candidate = Path(path_value).expanduser().resolve()
    if not any(str(candidate).lower() == str(root).lower() or _is_relative_to(candidate, root) for root in roots):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该路径不在允许浏览的范围内。")
    return candidate


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _browser_value(path: Path, kind: str) -> str:
    if kind == "weights":
        return path.relative_to(OUTPUTS_DIR.resolve()).as_posix()
    if kind == "config":
        return path.relative_to(REPO_ROOT).as_posix()
    return str(path)


@router.get("/models")
def fetch_model_state(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ = current_user
    return _success(_serialize_model_state(db))


@router.get("/model-profiles")
def fetch_model_profiles(db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    profiles = db.query(ModelProfile).options(joinedload(ModelProfile.revisions)).order_by(ModelProfile.display_order.asc(), ModelProfile.id.asc()).all()
    return _success({"items": [_serialize_profile_with_status(db, profile) for profile in profiles]})


@router.post("/model-profiles")
def create_model_profile(
    payload: ModelProfilePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    profile_data = _profile_fields_from_payload(payload)
    _validate_profile_name(db, profile_data["name"])
    try:
        revision_data = normalize_revision_payload(payload.model_dump())
        validate_revision_files(type("RevisionCandidate", (), revision_data), require_exists=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if db.query(ModelRevision).filter(ModelRevision.signature == revision_data["signature"]).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="相同签名的模型版本已存在。")

    profile = create_profile_with_revision(db, profile_data, revision_data)
    _audit(audit_logger, current_user.id, f"新增模型档案 {profile.name}", True)
    return _success(_serialize_profile_with_status(db, profile), message="模型档案已创建。")


@router.patch("/model-profiles/{profile_id}")
def update_model_profile(
    profile_id: int,
    payload: ModelProfilePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")

    profile_data = _profile_fields_from_payload(payload, profile)
    if "name" in profile_data:
        _validate_profile_name(db, profile_data["name"], exclude_id=profile.id)
    for key, value in profile_data.items():
        setattr(profile, key, value)

    revision_keys = {"revision_name", "weights_file", "config_file", "supports_concat", "supports_rerank", "global_feature_dim", "full_feature_dim", "fast_inference_mode", "pro_inference_mode"}
    if revision_keys.intersection(payload.model_dump(exclude_unset=True).keys()):
        try:
            revision_data = normalize_revision_payload(_revision_source(profile, payload))
            validate_revision_files(type("RevisionCandidate", (), revision_data), require_exists=True)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        duplicate = db.query(ModelRevision).filter(ModelRevision.signature == revision_data["signature"], ModelRevision.model_profile_id != profile.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="相同签名的模型版本已属于其他档案。")
        create_revision_for_profile(db, profile, revision_data)

    db.commit()
    db.refresh(profile)
    _audit(audit_logger, current_user.id, f"更新模型档案 {profile.name}", True)
    return _success(_serialize_profile_with_status(db, profile), message="模型档案已更新。")


@router.delete("/model-profiles/{profile_id}")
def delete_model_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")

    if gallery_references_profile(db, profile.id):
        profile.is_enabled = False
        profile.is_public = False
        db.commit()
        _audit(audit_logger, current_user.id, f"停用模型档案 {profile.name}", True)
        return _success(_serialize_profile_with_status(db, profile), message="模型已有特征引用，已停用而不是硬删除。")

    name = profile.name
    profile.active_revision_id = None
    db.flush()
    for revision in list(profile.revisions):
        db.delete(revision)
    db.delete(profile)
    db.commit()
    _audit(audit_logger, current_user.id, f"删除模型档案 {name}", True)
    return _success(message="模型档案已删除。")


@router.post("/model-profiles/{profile_id}/publish")
def publish_model_profile(
    profile_id: int,
    payload: PublishPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")
    if not profile.is_enabled and payload.is_public:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="停用模型不能发布给用户。")
    profile.is_public = bool(payload.is_public)
    db.commit()
    _audit(audit_logger, current_user.id, f"{'发布' if profile.is_public else '取消发布'}模型档案 {profile.name}", True)
    return _success(_serialize_profile_with_status(db, profile))


@router.post("/model-profiles/{profile_id}/features/build")
def build_model_features(
    profile_id: int,
    background_tasks: BackgroundTasks,
    payload: FeatureBuildPayload = Body(default_factory=FeatureBuildPayload),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库特征任务正在运行。")

    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")
    revision = get_active_revision(profile)
    if not revision:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该模型还没有可用版本。")
    if db.query(func.count(GalleryImage.id)).scalar() == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先注册图库图片，再构建模型特征。")

    try:
        validate_revision_files(revision, require_exists=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    task = create_build_task(db, revision, actor_user_id=current_user.id, rebuild=payload.rebuild)
    background_tasks.add_task(run_feature_build_task, task.id, current_user.id)
    _audit(audit_logger, current_user.id, f"启动模型特征构建 {profile.name}", True)
    return _success({"task_id": task.id}, message="已开始构建该模型的图库特征。")


@router.delete("/model-profiles/{profile_id}/features")
def clear_model_features(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")
    revision = get_active_revision(profile)
    if not revision:
        return _success({"deleted": 0})
    deleted = clear_features_for_revision(db, revision.id)
    db.commit()
    _audit(audit_logger, current_user.id, f"清空模型特征 {profile.name}：{deleted} 条", True)
    return _success({"deleted": deleted}, message="该模型版本的图库特征已清空。")


@router.get("/model-profiles/{profile_id}/features/status")
def fetch_model_feature_status(profile_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    profile = get_profile_or_404(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型档案不存在。")
    revision = get_active_revision(profile)
    if not revision:
        return _success({"image_count": 0, "feature_count": 0, "missing_count": 0, "is_complete": False})
    return _success(get_revision_feature_status(db, revision))


@router.get("/gallery/images")
def fetch_gallery_images(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    return _success(list_gallery_images(db, page=page, size=size))


@router.post("/gallery/images/register-files")
def register_gallery_files(
    payload: RegisterFilesPayload,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin_user),
):
    paths = [str(item or "").strip() for item in payload.paths if str(item or "").strip()]
    if not paths:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择或输入图片路径。")
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")

    start_gallery_operation("register_files", "已提交图片注册任务。")
    background_tasks.add_task(run_register_files_task, paths, current_user.id)
    return _success({"started": True, "total": len(paths)}, message="已开始注册图片文件。")


@router.post("/gallery/images/register-folder")
def register_gallery_folder(
    payload: RegisterFolderPayload,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin_user),
):
    folder_path = str(payload.folder_path or "").strip()
    if not folder_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择图库目录。")
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")
    if not Path(folder_path).expanduser().resolve().is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"图片目录不存在：{folder_path}")

    start_gallery_operation("register_folder", "已提交目录注册任务。")
    background_tasks.add_task(run_register_folder_task, folder_path, payload.recursive, current_user.id)
    return _success({"started": True}, message="已开始注册目录图片。")


@router.delete("/gallery/images/{image_id}")
def remove_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    try:
        delete_gallery_image(db, image_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _audit(audit_logger, current_user.id, f"删除图库图片记录 {image_id}", True)
    return _success(message="图片记录已删除。")


@router.get("/file-browser")
def browse_files(
    path: Optional[str] = Query(default=None),
    kind: str = Query(default="image"),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    normalized_kind = str(kind or "image").lower()
    roots = _resolve_browser_roots(normalized_kind)
    current_path = _safe_browser_path(path, roots)
    if not current_path.exists() or not current_path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择一个可浏览的目录。")

    suffixes = {
        "weights": {".pth", ".pt"},
        "config": {".yml", ".yaml"},
        "image": set(load_system_config().get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)),
        "folder": set(),
    }.get(normalized_kind, set(load_system_config().get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)))

    entries = []
    for item in sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if item.is_dir():
            entries.append({"name": item.name, "path": str(item), "value": str(item), "type": "directory", "selectable": normalized_kind == "folder"})
        elif not suffixes or item.suffix.lower() in suffixes:
            entries.append({"name": item.name, "path": str(item), "value": _browser_value(item.resolve(), normalized_kind), "type": "file", "selectable": normalized_kind != "folder"})

    return _success({"path": str(current_path), "roots": [str(root) for root in roots], "entries": entries})


@router.get("/gallery/status")
def get_gallery_status(current_user: User = Depends(require_admin_user)):
    _ = current_user
    return _success(dict(sync_status))


@router.post("/gallery/clear")
def clear_all_gallery_features(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="图库任务运行中，暂时不能清空特征。")
    deleted = db.query(GalleryFeature).delete(synchronize_session=False)
    db.commit()
    _audit(audit_logger, current_user.id, f"清空全部图库特征 {deleted} 条", True)
    return _success({"deleted": int(deleted)}, message="全部图库特征已清空，图片记录保留。")


@router.post("/gallery/sync")
def compatibility_sync_gallery(current_user: User = Depends(require_admin_user)):
    _ = current_user
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="请在模型配置模块中为指定模型构建特征。")


@router.post("/gallery/rebuild")
def compatibility_rebuild_gallery(current_user: User = Depends(require_admin_user)):
    _ = current_user
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="请在模型配置模块中为指定模型重新构建特征。")


@router.get("/overview")
def fetch_admin_overview(db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    return _success(_serialize_overview(db))


@router.get("/gallery/stats")
def fetch_gallery_stats(db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    return _success(_serialize_overview(db))


@router.get("/config")
def get_config(current_user: User = Depends(require_admin_user)):
    _ = current_user
    return _success(_serialize_config())


@router.post("/config")
def update_config(
    config_in: ConfigUpdate,
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    next_config = {
        "model_device": config_in.model_device,
        "similarity_threshold": config_in.similarity_threshold,
        "max_results": config_in.max_results,
        "search_default_top_k": config_in.search_default_top_k,
        "max_deep_thinking_gallery_size": config_in.max_deep_thinking_gallery_size,
        "gallery_poll_interval_ms": config_in.gallery_poll_interval_ms,
        "allowed_query_suffixes": config_in.allowed_query_suffixes,
        "file_browser_roots": config_in.file_browser_roots,
        "log_level": config_in.log_level,
    }
    try:
        reid_engine.configure(device=config_in.model_device, eager=reid_engine.initialized)
        saved_config = save_system_config(next_config)
        configure_logging(saved_config.get("log_level", "INFO"))
    except ValueError as exc:
        _audit(audit_logger, current_user.id, "更新系统参数失败", False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Failed to update admin config")
        _audit(audit_logger, current_user.id, "更新系统参数失败", False)
        raise

    _audit(audit_logger, current_user.id, "更新系统参数", True)
    return _success(_serialize_config(), message="系统配置已更新。")


@router.get("/logs", response_model=AuditLogResponse)
def fetch_audit_logs(page: int = 1, size: int = 20, db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    offset_value = max(page - 1, 0) * size
    total_count = db.query(SysLog).count()
    log_records = db.query(SysLog).order_by(SysLog.exec_time.desc()).offset(offset_value).limit(size).all()
    return _success({"total": total_count, "items": log_records})


@router.get("/users")
def fetch_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin_user)):
    _ = current_user
    users = db.query(User).order_by(User.id.asc()).all()
    return _success([_serialize_user(user) for user in users])


@router.post("/users")
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    username = user_in.username.strip()
    if not username or not user_in.password.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名和密码不能为空。")
    role = _ensure_valid_role(user_in.role)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在。")
    new_user = User(username=username, password=get_password_hash(user_in.password), role=role, is_builtin=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    _audit(audit_logger, current_user.id, f"创建账号 {username}", True)
    return _success(_serialize_user(new_user), message="账号创建成功。")


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在。")

    if user_in.username is not None:
        username = user_in.username.strip()
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空。")
        duplicate = db.query(User).filter(User.username == username, User.id != user.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在。")
        user.username = username

    if user_in.role is not None:
        role = _ensure_valid_role(user_in.role)
        if user.is_builtin and role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="内置账号不能降级为普通用户。")
        user.role = role

    if user_in.password is not None and user_in.password.strip():
        user.password = get_password_hash(user_in.password)

    db.commit()
    db.refresh(user)
    _audit(audit_logger, current_user.id, f"更新账号 {user.username}", True)
    return _success(_serialize_user(user), message="账号信息已更新。")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在。")
    if user.is_builtin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="系统内置账号不可删除。")
    username = user.username
    db.delete(user)
    db.commit()
    _audit(audit_logger, current_user.id, f"删除账号 {username}", True)
    return _success(message="账号已删除。")
