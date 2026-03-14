from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db, SessionLocal
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.models.vehicle import VehicleFeature
from app.schemas.audit_schema import AuditLogResponse
from app.core.security import get_password_hash
from pydantic import BaseModel
from app.services.gallery_service import run_sync_task, clear_gallery_db, sync_status
from app.api.endpoints.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

router = APIRouter()

dynamic_config = {
    "model_device": "cpu",
    "similarity_threshold": 0.5,
    "max_results": 50,
    "log_level": "INFO"
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
        return {"code": 400, "message": "账户实体已存在"}
    new_user = User(username=user_in.username, password=get_password_hash(user_in.password), role=user_in.role)
    db.add(new_user)
    db.commit()
    return {"code": 200, "message": "success"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    if user_id == 1:
        return {"code": 403, "message": "系统初始管理员不可移除"}
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 404, "message": "账户不存在"}
    db.delete(user)
    db.commit()
    return {"code": 200, "message": "success"}

@router.post("/gallery/sync")
def sync_gallery(background_tasks: BackgroundTasks):
    if sync_status["is_running"]:
        return {"code": 400, "message": "计算引擎运行中"}
    db = SessionLocal()
    background_tasks.add_task(run_sync_task, db)
    return {"code": 200, "message": "增量同步指令已送达"}

@router.post("/gallery/clear")
def clear_gallery(db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        return {"code": 400, "message": "引擎运行中拒绝清理指令"}
    clear_gallery_db(db)
    return {"code": 200, "message": "物理底库已销毁"}

@router.post("/gallery/rebuild")
def rebuild_gallery(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if sync_status["is_running"]:
        return {"code": 400, "message": "计算引擎运行中"}
    clear_gallery_db(db)
    new_db = SessionLocal()
    background_tasks.add_task(run_sync_task, new_db)
    return {"code": 200, "message": "底库已重置并拉起全量重建管线"}

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
            "latest_ingestion_time": latest_time_str
        }
    }

@router.get("/config")
def get_config():
    return {"code": 200, "message": "success", "data": dynamic_config}

@router.post("/config")
def update_config(config_in: ConfigUpdate):
    dynamic_config["model_device"] = config_in.model_device
    dynamic_config["similarity_threshold"] = config_in.similarity_threshold
    dynamic_config["max_results"] = config_in.max_results
    dynamic_config["log_level"] = config_in.log_level
    return {"code": 200, "message": "配置更新成功"}