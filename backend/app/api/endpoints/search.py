import logging
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
from app.core.system_config import DEFAULT_ALLOWED_QUERY_SUFFIXES, load_system_config
from app.db.session import get_db
from app.engine.predictor import reid_engine
from app.models.user import User
from app.models.vehicle import VehicleFeature
from app.services.search_service import SearchService


router = APIRouter()
logger = logging.getLogger(__name__)


def _get_safe_suffix(filename: Optional[str], allowed_suffixes: set[str]) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix or suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"当前仅支持这些查询图片格式：{', '.join(sorted(allowed_suffixes))}",
        )

    return suffix


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
        gallery_records = db.query(VehicleFeature).count()
        allowed_suffixes = {
            suffix.lower()
            for suffix in runtime_config.get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
        }

        if gallery_model_file and gallery_model_file != current_model_file:
            audit_logger(user_id=current_user.id, operation="车辆检索失败：图库模型不一致", status=False)
            raise HTTPException(
                status_code=409,
                detail="当前模型与图库特征使用的模型不一致，请联系管理员重新处理图库后再检索。",
            )

        if gallery_records > 0 and not gallery_model_file:
            audit_logger(user_id=current_user.id, operation="车辆检索失败：图库模型未知", status=False)
            raise HTTPException(
                status_code=409,
                detail="当前图库特征尚未记录使用的模型，请联系管理员重新处理全部图片后再检索。",
            )

        effective_top_k = max(1, min(int(top_k), int(runtime_config.get("max_results", 50))))
        upload_dir = Path(settings.SEARCH_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        fd, temp_filename = tempfile.mkstemp(
            prefix="query_",
            suffix=_get_safe_suffix(file.filename, allowed_suffixes),
            dir=upload_dir,
        )

        start_time = time.time()
        with os.fdopen(fd, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        service = SearchService(db)
        results = service.search(
            img_path=temp_filename,
            top_k=effective_top_k,
            similarity_threshold=float(runtime_config.get("similarity_threshold", 0.0)),
        )
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
    except HTTPException as exc:
        detail = str(getattr(exc, "detail", "")).strip()
        if exc.status_code != 409:
            audit_logger(user_id=current_user.id, operation="车辆检索失败：请求被拒绝", status=False)
        elif not detail:
            audit_logger(user_id=current_user.id, operation="车辆检索失败", status=False)
        raise
    except Exception:
        logger.exception("Vehicle search failed for user_id=%s", current_user.id)
        audit_logger(user_id=current_user.id, operation="车辆检索失败：系统异常", status=False)
        raise HTTPException(status_code=500, detail="车辆检索执行失败，请稍后重试或联系管理员。")
    finally:
        await file.close()
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
