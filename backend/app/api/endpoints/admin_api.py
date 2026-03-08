from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.sys_log_model import SysLog
from app.models.user import User
from app.schemas.audit_schema import AuditLogResponse
from app.core.security import get_password_hash
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

@router.get("/logs", response_model=AuditLogResponse)
def fetch_audit_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db)
):
    offset_value = (page - 1) * size
    total_count = db.query(SysLog).count()
    log_records = db.query(SysLog).order_by(SysLog.exec_time.desc()).offset(offset_value).limit(size).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "total": total_count,
            "items": log_records
        }
    }

@router.get("/users")
def fetch_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "create_time": u.create_time
        })
    return {
        "code": 200,
        "message": "success",
        "data": user_list
    }

@router.post("/users")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        return {"code": 400, "message": "账户已存在"}
    
    new_user = User(
        username=user_in.username,
        password=get_password_hash(user_in.password),
        role=user_in.role
    )
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
def sync_gallery():
    return {"code": 200, "message": "底库同步指令已送达"}