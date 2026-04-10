import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.endpoints.auth import get_current_user
from app.api.response_utils import success_response
from app.core.audit_logger import get_audit_logger
from app.core.config import settings
from app.core.system_config import load_system_config
from app.db.session import get_db
from app.engine.predictor import reid_engine
from app.models.user import User
from app.services.search_service import SearchService


router = APIRouter()
ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _get_safe_suffix(filename: Optional[str]) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in ALLOWED_UPLOAD_SUFFIXES else ".img"


@router.post("/search")
async def search_vehicle(
    file: UploadFile = File(...),
    top_k: int = Form(10),
    db: Session = Depends(get_db),
    audit_logger: Callable = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user),
):
    temp_filename = ""

    try:
        runtime_config = load_system_config()
        gallery_model_file = runtime_config.get("gallery_model_file", "")
        current_model_file = reid_engine.get_current_weight_file()

        if gallery_model_file and gallery_model_file != current_model_file:
            raise HTTPException(
                status_code=409,
                detail="当前模型与图库特征使用的模型不一致，请联系管理员重新处理图库后再检索。",
            )

        effective_top_k = max(1, min(int(top_k), int(runtime_config.get("max_results", 50))))
        upload_dir = Path(settings.SEARCH_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        fd, temp_filename = tempfile.mkstemp(
            prefix="query_",
            suffix=_get_safe_suffix(file.filename),
            dir=upload_dir,
        )

        start_time = time.time()
        with os.fdopen(fd, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        service = SearchService(db)
        results = service.search(img_path=temp_filename, top_k=effective_top_k)
        cost_time = time.time() - start_time

        audit_logger(
            user_id=current_user.id,
            operation=f"执行车辆图像检索，返回 {len(results)} 条结果",
            status=True,
        )

        return success_response(
            {
                "time_cost": round(cost_time, 4),
                "total_found": len(results),
                "results": results,
            }
        )
    except HTTPException:
        audit_logger(user_id=current_user.id, operation="车辆检索任务执行异常", status=False)
        raise
    except Exception as exc:
        audit_logger(user_id=current_user.id, operation="车辆检索任务执行异常", status=False)
        raise HTTPException(status_code=500, detail=str(exc) or "车辆检索执行失败。") from exc
    finally:
        await file.close()
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
