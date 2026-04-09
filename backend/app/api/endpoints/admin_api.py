from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.endpoints.auth import get_current_user
from app.core.model_preferences import get_default_model_file
from app.core.security import get_password_hash
from app.db.session import SessionLocal, get_db
from app.engine.predictor import reid_engine
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.models.vehicle import VehicleFeature
from app.schemas.audit_schema import AuditLogResponse
from app.services.gallery_service import clear_gallery_db, run_sync_task, sync_status

router = APIRouter(dependencies=[Depends(get_current_user)])


dynamic_config = {
    "model_device": reid_engine.device_name,
    "similarity_threshold": 0.5,
    "max_results": 50,
    "log_level": "INFO",
    "current_model_file": reid_engine.get_current_weight_file(),
}


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class ConfigUpdate(BaseModel):
    model_device: str
    similarity_threshold: float
    max_results: int
    log_level: str


class ModelSelectRequest(BaseModel):
    model_file: str


def serialize_config():
    dynamic_config["model_device"] = reid_engine.device_name
    dynamic_config["current_model_file"] = reid_engine.get_current_weight_file()
    dynamic_config["default_model_file"] = get_default_model_file() or reid_engine.get_current_weight_file()
    return dict(dynamic_config)


@router.get("/logs", response_model=AuditLogResponse)
def fetch_audit_logs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    offset_value = (page - 1) * size
    total_count = db.query(SysLog).count()
    log_records = db.query(SysLog).order_by(SysLog.exec_time.desc()).offset(offset_value).limit(size).all()
    return {"code": 200, "message": "success", "data": {"total": total_count, "items": log_records}}


@router.get("/users")
def fetch_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    user_list = [{"id": u.id, "username": u.username, "role": u.role, "create_time": u.create_time} for u in users]
    return {"code": 200, "message": "success", "data": user_list}


@router.post("/users")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        return {"code": 400, "message": "账号已存在"}

    new_user = User(username=user_in.username, password=get_password_hash(user_in.password), role=user_in.role)
    db.add(new_user)
    db.commit()
    return {"code": 200, "message": "success"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    if user_id == 1:
        return {"code": 403, "message": "系统初始管理员不可删除"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 404, "message": "账号不存在"}

    db.delete(user)
    db.commit()
    return {"code": 200, "message": "success"}


@router.post("/gallery/sync")
def sync_gallery(background_tasks: BackgroundTasks):
    if sync_status["is_running"]:
        return {"code": 400, "message": "当前已有图库任务正在运行"}

    db = SessionLocal()
    background_tasks.add_task(run_sync_task, db)
    return {"code": 200, "message": "已开始处理新图片"}


@router.post("/gallery/clear")
def clear_gallery(db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        return {"code": 400, "message": "图库任务运行中，暂时不能清空记录"}

    clear_gallery_db(db)
    return {"code": 200, "message": "图库记录已清空"}


@router.post("/gallery/rebuild")
def rebuild_gallery(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        return {"code": 400, "message": "当前已有图库任务正在运行"}

    clear_gallery_db(db)
    new_db = SessionLocal()
    background_tasks.add_task(run_sync_task, new_db)
    return {"code": 200, "message": "已开始重新处理全部图库图片"}


@router.get("/gallery/status")
def get_gallery_status():
    return {"code": 200, "message": "success", "data": {"is_running": sync_status["is_running"], "logs": sync_status["logs"]}}


@router.get("/gallery/stats")
def get_system_stats(db: Session = Depends(get_db)):
    total_images = db.query(VehicleFeature).count()
    total_vehicles = db.query(func.count(func.distinct(VehicleFeature.vehicle_id))).scalar() or 0
    latest_record = db.query(func.max(VehicleFeature.create_time)).scalar()
    latest_time_str = latest_record.strftime("%Y-%m-%d %H:%M:%S") if latest_record else "暂无记录"
    return {
        "code": 200,
        "message": "success",
        "data": {
            "total_images": total_images,
            "total_vehicles": total_vehicles,
            "latest_ingestion_time": latest_time_str,
        },
    }


@router.get("/config")
def get_config():
    return {"code": 200, "message": "success", "data": serialize_config()}


@router.post("/config")
def update_config(config_in: ConfigUpdate):
    try:
        reid_engine.configure(device=config_in.model_device, eager=reid_engine.initialized)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    dynamic_config["model_device"] = reid_engine.device_name
    dynamic_config["similarity_threshold"] = config_in.similarity_threshold
    dynamic_config["max_results"] = config_in.max_results
    dynamic_config["log_level"] = config_in.log_level
    dynamic_config["current_model_file"] = reid_engine.get_current_weight_file()

    return {"code": 200, "message": "配置已更新", "data": serialize_config()}
