import shutil
import os
import time
from typing import Callable
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search_service import SearchService
from app.core.audit_logger import get_audit_logger
from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/search")
async def search_vehicle(
    file: UploadFile = File(...),
    top_k: int = Form(10),
    db: Session = Depends(get_db),
    audit_logger: Callable = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
):
    os.makedirs("temp", exist_ok=True)
    temp_filename = f"temp/query_{int(time.time())}_{file.filename}"
    
    try:
        start_time = time.time()
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        service = SearchService(db)
        results = service.search(img_path=temp_filename, top_k=top_k)
        cost_time = time.time() - start_time
        
        audit_logger(user_id=current_user.id, operation=f"执行车辆图像检索，返回 {len(results)} 条结果", status=True)
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "time_cost": round(cost_time, 4),
                "total_found": len(results),
                "results": results
            }
        }
        
    except Exception as e:
        audit_logger(user_id=current_user.id, operation="车辆检索任务执行异常", status=False)
        return {"code": 500, "message": str(e)}
        
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass