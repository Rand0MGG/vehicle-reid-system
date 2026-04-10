import logging
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.endpoints.auth import get_current_user, require_admin_user
from app.api.response_utils import success_response
from app.core.audit_logger import get_audit_logger
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.security import get_password_hash
from app.core.system_config import (
    DEFAULT_ALLOWED_QUERY_SUFFIXES,
    has_gallery_model_mismatch,
    load_system_config,
    save_system_config,
)
from app.db.session import get_db
from app.engine.predictor import reid_engine
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.models.vehicle import VehicleFeature
from app.schemas.audit_schema import AuditLogResponse
from app.services.gallery_service import (
    clear_gallery_db,
    open_gallery_folder,
    run_sync_task,
    sync_status,
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
    gallery_poll_interval_ms: int
    allowed_query_suffixes: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_QUERY_SUFFIXES))
    log_level: str


class ModelSelectRequest(BaseModel):
    model_file: str


def _success(data=None, message: str = "success"):
    return success_response(data=data, message=message)


def _format_datetime(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "暂无记录"


def _ensure_valid_role(role: str) -> str:
    normalized_role = str(role).strip().lower()
    if normalized_role not in {"admin", "user"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号角色只能是 admin 或 user。",
        )
    return normalized_role


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_builtin": bool(user.is_builtin),
        "create_time": user.create_time,
    }


def _serialize_model_state(db: Session) -> dict:
    config = load_system_config()
    current_model_file = reid_engine.get_current_weight_file()
    gallery_model_file = config.get("gallery_model_file", "")
    available_models = reid_engine.list_weight_files()
    gallery_feature_count = db.query(VehicleFeature).count()

    return {
        "current_model_file": current_model_file,
        "gallery_model_file": gallery_model_file,
        "gallery_model_matches_current": not has_gallery_model_mismatch(
            {
                "current_model_file": current_model_file,
                "gallery_model_file": gallery_model_file,
            }
        ),
        "gallery_model_known": bool(gallery_model_file),
        "gallery_has_records": gallery_feature_count > 0,
        "gallery_feature_count": gallery_feature_count,
        "available_models": available_models,
        "available_model_count": len(available_models),
        "initialized": reid_engine.initialized,
        "model_device": reid_engine.device_name,
        "max_results": int(config.get("max_results", 50)),
        "search_default_top_k": int(config.get("search_default_top_k", 10)),
        "allowed_query_suffixes": config.get(
            "allowed_query_suffixes",
            list(DEFAULT_ALLOWED_QUERY_SUFFIXES),
        ),
    }


def _serialize_config(db: Session) -> dict:
    config = load_system_config()
    model_state = _serialize_model_state(db)

    return {
        "model_device": reid_engine.device_name,
        "similarity_threshold": float(config.get("similarity_threshold", 0.5)),
        "max_results": int(config.get("max_results", 50)),
        "search_default_top_k": int(config.get("search_default_top_k", 10)),
        "gallery_poll_interval_ms": int(config.get("gallery_poll_interval_ms", 1500)),
        "allowed_query_suffixes": config.get(
            "allowed_query_suffixes",
            list(DEFAULT_ALLOWED_QUERY_SUFFIXES),
        ),
        "log_level": config.get("log_level", "INFO"),
        "current_model_file": model_state["current_model_file"],
        "gallery_model_file": model_state["gallery_model_file"],
        "gallery_model_matches_current": model_state["gallery_model_matches_current"],
        "gallery_has_records": model_state["gallery_has_records"],
        "initialized": model_state["initialized"],
        "gallery_dir": str(Path(settings.GALLERY_DIR).resolve()),
        "search_upload_dir": str(Path(settings.SEARCH_UPLOAD_DIR).resolve()),
    }


def _serialize_overview(db: Session) -> dict:
    total_images = db.query(VehicleFeature).count()
    total_vehicles = db.query(func.count(func.distinct(VehicleFeature.vehicle_id))).scalar() or 0
    latest_ingestion_time = db.query(func.max(VehicleFeature.create_time)).scalar()
    latest_log_time = db.query(func.max(SysLog.exec_time)).scalar()
    total_users = db.query(User).count()
    total_logs = db.query(SysLog).count()
    model_state = _serialize_model_state(db)

    return {
        "total_images": total_images,
        "total_vehicles": total_vehicles,
        "latest_ingestion_time": _format_datetime(latest_ingestion_time),
        "current_model_file": model_state["current_model_file"],
        "gallery_model_file": model_state["gallery_model_file"],
        "gallery_model_matches_current": model_state["gallery_model_matches_current"],
        "gallery_model_known": model_state["gallery_model_known"],
        "available_model_count": model_state["available_model_count"],
        "model_device": model_state["model_device"],
        "initialized": model_state["initialized"],
        "gallery_task_running": bool(sync_status["is_running"]),
        "gallery_task_state": "running" if sync_status["is_running"] else "idle",
        "total_users": total_users,
        "total_logs": total_logs,
        "latest_log_time": _format_datetime(latest_log_time),
        "gallery_dir": str(Path(settings.GALLERY_DIR).resolve()),
        "search_upload_dir": str(Path(settings.SEARCH_UPLOAD_DIR).resolve()),
    }


def _audit(
    audit_logger: Callable[[Optional[int], str, bool], None],
    user_id: Optional[int],
    operation: str,
    status: bool,
) -> None:
    audit_logger(user_id=user_id, operation=operation, status=status)


@router.get("/models")
def fetch_model_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return _success(_serialize_model_state(db))


@router.post("/models/select")
def apply_current_model(
    request: ModelSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    model_file = request.model_file.strip()
    if not model_file:
        _audit(audit_logger, current_user.id, "切换当前模型失败：未选择模型文件", False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择一个模型文件。")

    try:
        reid_engine.configure(weights_file=model_file, eager=reid_engine.initialized)
    except ValueError as exc:
        _audit(audit_logger, current_user.id, "切换当前模型失败", False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    save_system_config({"current_model_file": model_file})
    _audit(audit_logger, current_user.id, f"切换当前模型为 {model_file}", True)
    return _success(_serialize_model_state(db), message="当前模型已更新")


@router.get("/logs", response_model=AuditLogResponse)
def fetch_audit_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    offset_value = max(page - 1, 0) * size
    total_count = db.query(SysLog).count()
    log_records = db.query(SysLog).order_by(SysLog.exec_time.desc()).offset(offset_value).limit(size).all()
    return _success({"total": total_count, "items": log_records})


@router.get("/overview")
def fetch_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    return _success(_serialize_overview(db))


@router.get("/gallery/stats")
def fetch_gallery_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    return _success(_serialize_overview(db))


@router.get("/users")
def fetch_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
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
        _audit(audit_logger, current_user.id, "创建账号失败：用户名或密码为空", False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名和密码不能为空。")

    role = _ensure_valid_role(user_in.role)
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        _audit(audit_logger, current_user.id, f"创建账号失败：用户名 {username} 已存在", False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在。")

    new_user = User(
        username=username,
        password=get_password_hash(user_in.password),
        role=role,
        is_builtin=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    _audit(audit_logger, current_user.id, f"创建账号 {username}", True)
    return _success(_serialize_user(new_user), message="账号创建成功")


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
        _audit(audit_logger, current_user.id, "更新账号失败：账号不存在", False)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在。")

    changes = []

    if user_in.username is not None:
        username = user_in.username.strip()
        if not username:
            _audit(audit_logger, current_user.id, f"更新账号失败：账号 {user.id} 用户名为空", False)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空。")

        duplicated_user = db.query(User).filter(User.username == username, User.id != user.id).first()
        if duplicated_user:
            _audit(audit_logger, current_user.id, f"更新账号失败：用户名 {username} 已存在", False)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在。")

        if username != user.username:
            user.username = username
            changes.append("用户名")

    if user_in.role is not None:
        role = _ensure_valid_role(user_in.role)
        if user.is_builtin and role != "admin":
            _audit(audit_logger, current_user.id, f"更新账号失败：内置账号 {user.username} 不可降级", False)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="内置账号不能降级为普通用户。",
            )

        if role != user.role:
            user.role = role
            changes.append("角色")

    if user_in.password is not None and user_in.password.strip():
        user.password = get_password_hash(user_in.password)
        changes.append("密码")

    if not changes:
        return _success(_serialize_user(user), message="没有需要更新的内容")

    db.commit()
    db.refresh(user)
    _audit(audit_logger, current_user.id, f"更新账号 {user.username}：{', '.join(changes)}", True)
    return _success(_serialize_user(user), message="账号信息已更新")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        _audit(audit_logger, current_user.id, "删除账号失败：账号不存在", False)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在。")

    if user.is_builtin:
        _audit(audit_logger, current_user.id, f"删除账号失败：内置账号 {user.username} 不可删除", False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统内置账号不可删除。",
        )

    username = user.username
    db.delete(user)
    db.commit()
    _audit(audit_logger, current_user.id, f"删除账号 {username}", True)
    return _success(message="账号已删除")


@router.post("/gallery/sync")
def sync_gallery(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    if sync_status["is_running"]:
        _audit(audit_logger, current_user.id, "图库增量处理失败：已有任务运行中", False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")

    model_state = _serialize_model_state(db)

    if model_state["gallery_model_file"] and not model_state["gallery_model_matches_current"]:
        _audit(audit_logger, current_user.id, "图库增量处理失败：模型不一致", False)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前模型与图库特征使用的模型不一致，请先重新处理全部图片。",
        )

    if model_state["gallery_has_records"] and not model_state["gallery_model_known"]:
        _audit(audit_logger, current_user.id, "图库增量处理失败：图库模型未知", False)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前图库特征尚未记录使用的模型，请先重新处理全部图片一次。",
        )

    background_tasks.add_task(run_sync_task, False, current_user.id, "图库增量处理")
    _audit(audit_logger, current_user.id, "启动图库增量处理任务", True)
    return _success(message="已开始处理新导入的图片")


@router.post("/gallery/clear")
def clear_gallery(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    if sync_status["is_running"]:
        _audit(audit_logger, current_user.id, "清空图库失败：任务运行中", False)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="图库任务运行中，暂时不能清空记录。",
        )

    clear_gallery_db(db)
    _audit(audit_logger, current_user.id, "清空图库记录", True)
    return _success(message="图库记录已清空")


@router.post("/gallery/rebuild")
def rebuild_gallery(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    if sync_status["is_running"]:
        _audit(audit_logger, current_user.id, "图库全量重建失败：已有任务运行中", False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")

    background_tasks.add_task(run_sync_task, True, current_user.id, "图库全量重建")
    _audit(audit_logger, current_user.id, "启动图库全量重建任务", True)
    return _success(message="已开始重新处理全部图片")


@router.post("/gallery/open-folder")
def open_gallery_directory(
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    opened, folder_path = open_gallery_folder()
    _audit(
        audit_logger,
        current_user.id,
        "打开图库文件夹" if opened else "打开图库文件夹失败",
        opened,
    )
    return _success(
        {"opened": opened, "path": folder_path},
        message="已尝试打开图库目录。" if opened else "当前环境不支持自动打开图库目录，请直接使用路径。",
    )


@router.get("/gallery/status")
def get_gallery_status(current_user: User = Depends(require_admin_user)):
    _ = current_user
    return _success({"is_running": sync_status["is_running"], "logs": sync_status["logs"]})


@router.get("/config")
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _ = current_user
    return _success(_serialize_config(db))


@router.post("/config")
def update_config(
    config_in: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
    audit_logger: Callable = Depends(get_audit_logger),
):
    next_config = {
        "model_device": config_in.model_device,
        "similarity_threshold": config_in.similarity_threshold,
        "max_results": config_in.max_results,
        "search_default_top_k": config_in.search_default_top_k,
        "gallery_poll_interval_ms": config_in.gallery_poll_interval_ms,
        "allowed_query_suffixes": config_in.allowed_query_suffixes,
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
    return _success(_serialize_config(db), message="系统配置已更新")
