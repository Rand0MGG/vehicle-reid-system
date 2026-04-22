import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.endpoints.auth import get_current_user
from app.api.response_utils import success_response
from app.core.audit_logger import get_audit_logger
from app.core.config import settings
from app.core.system_config import DEFAULT_ALLOWED_QUERY_SUFFIXES, load_system_config
from app.db.session import get_db
from app.models.model_profile import ModelProfile
from app.models.user import User
from app.models.vehicle import GalleryFeature, GalleryImage
from app.services.model_profile_service import get_active_revision, get_public_profiles, serialize_profile
from app.services.search_service import SearchService


router = APIRouter()
logger = logging.getLogger(__name__)


def _get_safe_suffix(filename: Optional[str], allowed_suffixes: set[str]) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix or suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前仅支持这些查询图片格式：{', '.join(sorted(allowed_suffixes))}",
        )
    return suffix


def _get_public_profile_or_404(db: Session, profile_id: int) -> ModelProfile:
    profile = (
        db.query(ModelProfile)
        .filter(
            ModelProfile.id == profile_id,
            ModelProfile.is_enabled.is_(True),
            ModelProfile.is_public.is_(True),
        )
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不可用或未公开。")
    return profile


@router.get("/models/public")
def fetch_public_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    config = load_system_config()
    profiles = get_public_profiles(db)
    return success_response(
        {
            "items": [serialize_profile(profile) for profile in profiles],
            "max_results": int(config.get("max_results", 50)),
            "search_default_top_k": int(config.get("search_default_top_k", 10)),
            "allowed_query_suffixes": config.get("allowed_query_suffixes", list(DEFAULT_ALLOWED_QUERY_SUFFIXES)),
        }
    )


@router.get("/gallery/images/{image_id}/file")
def read_gallery_image_file(image_id: int, db: Session = Depends(get_db)):
    image = db.query(GalleryImage).filter(GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片记录不存在。")

    path = Path(image.img_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片文件不存在。")

    return FileResponse(str(path))


@router.post("/search")
async def search_vehicle(
    file: UploadFile = File(...),
    top_k: int = Form(10),
    model_profile_id: int = Form(...),
    search_mode: str = Form("fast"),
    deep_thinking: bool = Form(False),
    db: Session = Depends(get_db),
    audit_logger: Callable = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user),
):
    temp_filename = ""

    try:
        runtime_config = load_system_config()
        profile = _get_public_profile_or_404(db, int(model_profile_id))
        revision = get_active_revision(profile)
        if not revision:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该模型还没有可用版本，请联系管理员配置模型。")

        normalized_search_mode = str(search_mode or "fast").strip().lower()
        allowed_suffixes = {
            suffix.lower()
            for suffix in runtime_config.get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
        }

        if normalized_search_mode not in {"fast", "pro"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="search_mode 只能是 fast 或 pro。")
        if normalized_search_mode == "pro" and not revision.supports_concat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前模型不支持 Pro 检索。")
        if deep_thinking and not revision.supports_rerank:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前模型不支持深度思考。")

        gallery_feature_count = (
            db.query(func.count(GalleryFeature.id))
            .filter(GalleryFeature.model_revision_id == revision.id)
            .scalar()
            or 0
        )
        gallery_image_count = db.query(func.count(GalleryImage.id)).scalar() or 0
        if gallery_image_count == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="图库还没有注册图片，请先由管理员注册图库图片。")
        if gallery_feature_count == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该模型还没有图库特征，请先由管理员为该模型构建特征。")
        if gallery_feature_count < gallery_image_count:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该模型图库特征尚未构建完整，请先由管理员补齐特征。")

        max_deep_thinking_gallery_size = int(runtime_config.get("max_deep_thinking_gallery_size", 5000))
        if deep_thinking and gallery_feature_count > max_deep_thinking_gallery_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"深度思考最多支持 {max_deep_thinking_gallery_size} 张图库图片，当前该模型有 {gallery_feature_count} 张。",
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
        search_result = service.search(
            img_path=temp_filename,
            revision=revision,
            top_k=effective_top_k,
            similarity_threshold=float(runtime_config.get("similarity_threshold", 0.0)),
            search_mode=normalized_search_mode,
            deep_thinking=bool(deep_thinking),
        )
        results = search_result["results"]
        cost_time = time.time() - start_time

        audit_logger(
            user_id=current_user.id,
            operation=f"执行车辆图像检索，模型 {profile.name}，模式 {normalized_search_mode}，返回 {len(results)} 条结果",
            status=True,
        )

        return success_response(
            {
                "time_cost": round(cost_time, 4),
                "total_found": len(results),
                "results": results,
                "model_profile_id": profile.id,
                "model_revision_id": revision.id,
                "search_mode": normalized_search_mode,
                "feature_dim": search_result["feature_dim"],
                "deep_thinking_requested": bool(deep_thinking),
                "deep_thinking_used": bool(search_result["deep_thinking_used"]),
            }
        )
    except HTTPException:
        raise
    except ValueError as exc:
        audit_logger(user_id=current_user.id, operation="车辆检索失败：模型或图库状态异常", status=False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        audit_logger(user_id=current_user.id, operation="车辆检索失败：文件缺失", status=False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Vehicle search failed for user_id=%s", current_user.id)
        audit_logger(user_id=current_user.id, operation="车辆检索失败：系统异常", status=False)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="车辆检索执行失败，请稍后重试或联系管理员。")
    finally:
        await file.close()
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
