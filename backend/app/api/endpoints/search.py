import shutil
import os
from fastapi import APIRouter, UploadFile, File
from app.engine.predictor import reid_engine

router = APIRouter()

@router.post("/search")
async def search_vehicle(file: UploadFile = File(...)):
    """
    HTTP POST 接口：处理图片上传与检索请求
    """
    # 1. 定义临时文件路径
    temp_filename = f"temp_{file.filename}"
    
    try:
        # 2. 将上传的图片流写入本地磁盘
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 3. 调用 AI 引擎提取特征
        # (这一步会验证上面的 predictor.py 是否工作正常)
        feature = reid_engine.extract_feature(temp_filename)
        
        # 4. 返回 JSON 结果给前端
        return {
            "code": 200,
            "filename": file.filename,
            "message": "Backend skeleton is working!",
            "feature_shape": feature.shape,  # 预期输出: (2048,)
            "note": "目前使用的是模拟特征数据"
        }
        
    except Exception as e:
        return {"code": 500, "message": str(e)}
        
    finally:
        # 5. 清理垃圾：删除临时图片
        if os.path.exists(temp_filename):
            os.remove(temp_filename)