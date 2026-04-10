from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user, require_admin_user
from app.api.response_utils import success_response
from app.core.system_config import has_gallery_model_mismatch, load_system_config, save_system_config
from app.engine.predictor import reid_engine


router = APIRouter()


class ModelSelectRequest(BaseModel):
    model_file: str



def serialize_model_state():
    config = load_system_config()
    current_model_file = reid_engine.get_current_weight_file()
    gallery_model_file = config.get("gallery_model_file", "")
    return {
        "current_model_file": current_model_file,
        "gallery_model_file": gallery_model_file,
        "gallery_model_matches_current": not has_gallery_model_mismatch(
            {
                "current_model_file": current_model_file,
                "gallery_model_file": gallery_model_file,
            }
        ),
        "available_models": reid_engine.list_weight_files(),
        "initialized": reid_engine.initialized,
        "model_device": reid_engine.device_name,
    }


@router.get("/models")
def fetch_model_files(current_user=Depends(get_current_user)):
    _ = current_user
    return success_response(serialize_model_state())


@router.post("/models/select")
def select_model_file(
    request: ModelSelectRequest,
    current_user=Depends(require_admin_user),
):
    _ = current_user
    model_file = request.model_file.strip()
    if not model_file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择一个模型文件。")

    try:
        reid_engine.configure(weights_file=model_file, eager=reid_engine.initialized)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    save_system_config({"current_model_file": model_file})
    return success_response(serialize_model_state(), message="当前模型已更新")
