from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user
from app.core.model_preferences import get_default_model_file, set_default_model_file
from app.engine.predictor import reid_engine

router = APIRouter(dependencies=[Depends(get_current_user)])


class ModelSelectRequest(BaseModel):
    model_file: str
    set_as_default: bool = False


@router.get("/models")
def fetch_model_files():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "current_model_file": reid_engine.get_current_weight_file(),
            "default_model_file": get_default_model_file() or reid_engine.get_current_weight_file(),
            "available_models": reid_engine.list_weight_files(),
            "initialized": reid_engine.initialized,
            "model_device": reid_engine.device_name,
        },
    }


@router.post("/models/select")
def select_model_file(request: ModelSelectRequest):
    reid_engine.configure(weights_file=request.model_file, eager=reid_engine.initialized)
    if request.set_as_default:
        set_default_model_file(request.model_file)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "current_model_file": reid_engine.get_current_weight_file(),
            "default_model_file": get_default_model_file() or reid_engine.get_current_weight_file(),
            "model_device": reid_engine.device_name,
        },
    }
