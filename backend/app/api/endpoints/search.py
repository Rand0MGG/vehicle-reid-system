# backend/app/api/endpoints/search.py
import shutil
import os
import time
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search_service import SearchService

router = APIRouter()

@router.post("/search")
async def search_vehicle(
    file: UploadFile = File(...),
    top_k: int = Form(10),  # 允许前端指定返回几条，默认10
    db: Session = Depends(get_db)
):
    """
    接收上传图片 -> 调用 SearchService -> 返回真实检索结果
    """
    # 1. 保存临时文件
    # 确保 temp 目录存在
    os.makedirs("temp", exist_ok=True)
    temp_filename = f"temp/query_{int(time.time())}_{file.filename}"
    
    try:
        start_time = time.time()
        
        # 写入磁盘
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. 初始化检索服务
        service = SearchService(db)
        
        # 3. 执行检索 (核心逻辑)
        results = service.search(img_path=temp_filename, top_k=top_k)
        
        cost_time = time.time() - start_time
        
        # 4. 构造标准返回格式
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
        print(f"❌ 检索出错: {str(e)}")
        return {"code": 500, "message": str(e)}
        
    finally:
        # 5. 清理现场
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass