from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.endpoints.auth import require_admin_user
from app.api.response_utils import success_response
from app.core.security import get_password_hash
from app.core.system_config import has_gallery_model_mismatch, load_system_config, save_system_config
from app.db.session import get_db
from app.engine.predictor import reid_engine
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.models.vehicle import VehicleFeature
from app.schemas.audit_schema import AuditLogResponse
from app.services.gallery_service import clear_gallery_db, run_sync_task, sync_status


router = APIRouter(dependencies=[Depends(require_admin_user)])


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class ConfigUpdate(BaseModel):
    model_device: str
    similarity_threshold: float
    max_results: int
    log_level: str



def _success(data=None, message: str = "success"):
    return success_response(data=data, message=message)



def serialize_config():
    config = load_system_config()
    current_model_file = reid_engine.get_current_weight_file()
    gallery_model_file = config.get("gallery_model_file", "")
    return {
        "model_device": reid_engine.device_name,
        "similarity_threshold": config["similarity_threshold"],
        "max_results": config["max_results"],
        "log_level": config["log_level"],
        "current_model_file": current_model_file,
        "gallery_model_file": gallery_model_file,
        "gallery_model_matches_current": not has_gallery_model_mismatch(
            {
                "current_model_file": current_model_file,
                "gallery_model_file": gallery_model_file,
            }
        ),
        "initialized": reid_engine.initialized,
    }


@router.get("/logs", response_model=AuditLogResponse)
def fetch_audit_logs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    offset_value = (page - 1) * size
    total_count = db.query(SysLog).count()
    log_records = db.query(SysLog).order_by(SysLog.exec_time.desc()).offset(offset_value).limit(size).all()
    return _success({"total": total_count, "items": log_records})


@router.get("/users")
def fetch_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    user_list = [{"id": u.id, "username": u.username, "role": u.role, "create_time": u.create_time} for u in users]
    return _success(user_list)


@router.post("/users")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.role not in {"admin", "user"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号角色只能是 admin 或 user。",
        )

    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在。")

    new_user = User(username=user_in.username, password=get_password_hash(user_in.password), role=user_in.role)
    db.add(new_user)
    db.commit()
    return _success(message="账号创建成功")


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    if user_id == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统初始管理员不可删除。",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在。")

    db.delete(user)
    db.commit()
    return _success(message="账号已删除")


@router.post("/gallery/sync")
def sync_gallery(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")

    config = serialize_config()
    gallery_records = db.query(VehicleFeature).count()

    if config["gallery_model_file"] and not config["gallery_model_matches_current"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前模型与图库特征使用的模型不一致，请先重新处理全部图片。",
        )

    if gallery_records > 0 and not config["gallery_model_file"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前图库特征尚未记录使用的模型，请先重新处理全部图片一次。",
        )

    background_tasks.add_task(run_sync_task)
    return _success(message="已开始处理新导入的图片")


@router.post("/gallery/clear")
def clear_gallery(db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="图库任务运行中，暂时不能清空记录。",
        )

    clear_gallery_db(db)
    return _success(message="图库记录已清空")


@router.post("/gallery/rebuild")
def rebuild_gallery(background_tasks: BackgroundTasks):
    if sync_status["is_running"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前已有图库任务正在运行。")

    background_tasks.add_task(run_sync_task, True)
    return _success(message="已开始重新处理全部图片")


@router.get("/gallery/status")
def get_gallery_status():
    return _success({"is_running": sync_status["is_running"], "logs": sync_status["logs"]})


@router.get("/gallery/stats")
def get_system_stats(db: Session = Depends(get_db)):
    total_images = db.query(VehicleFeature).count()
    total_vehicles = db.query(func.count(func.distinct(VehicleFeature.vehicle_id))).scalar() or 0
    latest_record = db.query(func.max(VehicleFeature.create_time)).scalar()
    latest_time_str = latest_record.strftime("%Y-%m-%d %H:%M:%S") if latest_record else "暂无记录"
    return _success(
        {
            "total_images": total_images,
            "total_vehicles": total_vehicles,
            "latest_ingestion_time": latest_time_str,
        }
    )


@router.get("/config")
def get_config():
    return _success(serialize_config())


@router.post("/config")
def update_config(config_in: ConfigUpdate):
    next_config = {
        "model_device": config_in.model_device,
        "similarity_threshold": config_in.similarity_threshold,
        "max_results": config_in.max_results,
        "log_level": config_in.log_level,
    }

    try:
        reid_engine.configure(device=config_in.model_device, eager=reid_engine.initialized)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    save_system_config(next_config)
    return _success(serialize_config(), message="系统配置已更新")
