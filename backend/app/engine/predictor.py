import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
import torch
from PIL import Image

from app.core.config import settings
from app.core.system_config import load_system_config
from app.services.model_profile_service import (
    compute_model_signature,
    list_weight_files,
    resolve_config_file,
    resolve_weights_file,
)


logger = logging.getLogger(__name__)


FASTREID_ROOT = Path(__file__).resolve().parents[3] / "fastreid"
sys.path.append(str(FASTREID_ROOT))

try:
    from fastreid.config import get_cfg
    from fastreid.data.transforms import build_transforms
    from fastreid.modeling import build_model
    from fastreid.utils.checkpoint import Checkpointer

    logger.info("FastReID library loaded successfully")
except ImportError:
    logger.exception("FastReID import failed")
    sys.exit(1)


@dataclass(frozen=True)
class RuntimeModelProfile:
    id: Optional[int]
    name: str
    weights_file: str
    config_file: str
    supports_concat: bool
    supports_rerank: bool
    global_feature_dim: int
    full_feature_dim: int
    fast_inference_mode: str
    pro_inference_mode: str
    is_active: bool = True

    @classmethod
    def from_profile(cls, profile: Any) -> "RuntimeModelProfile":
        revision = getattr(profile, "active_revision", None) or profile
        profile_name = getattr(profile, "name", None) or getattr(getattr(revision, "profile", None), "name", None)
        profile_id = getattr(profile, "id", None) if hasattr(profile, "active_revision") else getattr(revision, "model_profile_id", None)
        return cls(
            id=profile_id,
            name=str(profile_name or "Unnamed Model"),
            weights_file=str(getattr(revision, "weights_file", "") or ""),
            config_file=str(getattr(revision, "config_file", "") or ""),
            supports_concat=bool(getattr(revision, "supports_concat", False)),
            supports_rerank=bool(getattr(revision, "supports_rerank", False)),
            global_feature_dim=int(getattr(revision, "global_feature_dim", 2048) or 2048),
            full_feature_dim=int(getattr(revision, "full_feature_dim", 2048) or 2048),
            fast_inference_mode=str(getattr(revision, "fast_inference_mode", "global") or "global"),
            pro_inference_mode=str(getattr(revision, "pro_inference_mode", "global_detail") or "global_detail"),
            is_active=bool(getattr(profile, "is_enabled", True)),
        )

    @classmethod
    def legacy(cls) -> "RuntimeModelProfile":
        return cls(
            id=None,
            name="Legacy Baseline",
            weights_file=Path(settings.MODEL_WEIGHTS_FILE).name,
            config_file="configs/veri_r50ibn_sbs_s0_v1.yml",
            supports_concat=False,
            supports_rerank=True,
            global_feature_dim=2048,
            full_feature_dim=2048,
            fast_inference_mode="global",
            pro_inference_mode="global",
        )


class ReIDEngine:
    def __init__(self):
        self.model = None
        self.transforms = None
        self.device = None
        self.initialized = False
        self.runtime_profile = RuntimeModelProfile.legacy()
        self.weights_file = resolve_weights_file(self.runtime_profile.weights_file)
        self.config_file = resolve_config_file(self.runtime_profile.config_file)

        runtime_config = load_system_config()
        saved_device = runtime_config.get("model_device", settings.DEVICE)
        if saved_device == "cuda" and not torch.cuda.is_available():
            saved_device = "cpu"
        self.device_name = saved_device

    def _apply_runtime_profile(self, profile: RuntimeModelProfile) -> None:
        self.runtime_profile = profile
        self.weights_file = resolve_weights_file(profile.weights_file)
        self.config_file = resolve_config_file(profile.config_file)

    @staticmethod
    def _runtime_reload_key(profile: RuntimeModelProfile) -> tuple:
        return (
            profile.weights_file,
            profile.config_file,
            profile.supports_concat,
            profile.global_feature_dim,
            profile.full_feature_dim,
            profile.fast_inference_mode,
            profile.pro_inference_mode,
        )

    def list_weight_files(self):
        return list_weight_files()

    def list_config_files(self):
        from app.services.model_profile_service import list_config_files

        return list_config_files()

    def get_current_weight_file(self):
        return self.runtime_profile.weights_file

    def get_current_profile_name(self):
        return self.runtime_profile.name

    def get_current_signature(self):
        return compute_model_signature(self.runtime_profile)

    def configure(
        self,
        profile: Optional[Any] = None,
        weights_file: Optional[str] = None,
        device: Optional[str] = None,
        eager: bool = False,
    ):
        next_profile = self.runtime_profile
        if profile is not None:
            next_profile = RuntimeModelProfile.from_profile(profile)
        elif weights_file is not None:
            next_profile = RuntimeModelProfile(
                **{
                    **self.runtime_profile.__dict__,
                    "weights_file": weights_file,
                }
            )

        next_device = device or self.device_name
        if next_device not in {"cpu", "cuda"}:
            raise ValueError("运行设备只能是 cpu 或 cuda。")
        if next_device == "cuda" and not torch.cuda.is_available():
            raise ValueError("当前环境不可用 CUDA。")

        reload_required = (
            self._runtime_reload_key(next_profile) != self._runtime_reload_key(self.runtime_profile)
            or next_device != self.device_name
        )

        if reload_required:
            self._apply_runtime_profile(next_profile)
            self.device_name = next_device
            self.reset()
            if eager:
                self.setup()
            return

        self.runtime_profile = next_profile
        if eager and not self.initialized:
            self.setup()

    def reset(self):
        self.model = None
        self.transforms = None
        self.device = None
        self.initialized = False

    def setup(self):
        if self.initialized:
            return

        if not self.weights_file.exists():
            raise FileNotFoundError(f"模型权重文件不存在：{self.runtime_profile.weights_file}")
        if not self.config_file.exists():
            raise FileNotFoundError(f"推理配置文件不存在：{self.runtime_profile.config_file}")

        logger.info(
            "Loading ReID model profile=%s weights=%s config=%s",
            self.runtime_profile.name,
            self.weights_file,
            self.config_file,
        )

        cfg = get_cfg()
        cfg.merge_from_file(str(self.config_file))
        cfg.MODEL.BACKBONE.PRETRAIN = False
        cfg.MODEL.WEIGHTS = str(self.weights_file)
        cfg.MODEL.DEVICE = self.device_name

        self.model = build_model(cfg)
        self.model.eval()
        self._load_weights_or_raise()

        self.transforms = build_transforms(cfg, is_train=False)
        self.device = torch.device(cfg.MODEL.DEVICE)
        self.model.to(self.device)
        self.initialized = True
        logger.info("ReID engine initialized")

    def _load_weights_or_raise(self) -> None:
        checkpointer = Checkpointer(self.model)
        checkpoint = checkpointer._load_file(str(self.weights_file))
        incompatible = checkpointer._load_model(checkpoint)
        if incompatible is None:
            return

        incompatible_shapes = [
            item
            for item in incompatible.incorrect_shapes
            if not self._is_inference_unused_classifier_weight(item[0])
        ]
        if incompatible_shapes:
            examples = ", ".join(item[0] for item in incompatible_shapes[:5])
            raise ValueError(f"模型权重与推理结构不匹配，形状不一致的参数包括：{examples}")

        missing_keys = [
            key
            for key in incompatible.missing_keys
            if "num_batches_tracked" not in key
            and not self._is_inference_unused_classifier_weight(key)
        ]
        model_key_count = max(1, len(self.model.state_dict()))
        if len(missing_keys) > max(20, int(model_key_count * 0.5)):
            examples = ", ".join(missing_keys[:5])
            raise ValueError(f"模型权重与推理结构不匹配，缺少大量参数，例如：{examples}")

        checkpointer._log_incompatible_keys(incompatible)
        logger.info("Loaded model weights: %s", self.weights_file)

    @staticmethod
    def _is_inference_unused_classifier_weight(key: str) -> bool:
        if key == "heads.weight":
            return True
        if not key.startswith("heads.") or not key.endswith(".weight"):
            return False
        return len(key.split(".")) == 3

    def resolve_inference_mode(self, search_mode: str) -> str:
        normalized_mode = str(search_mode or "fast").strip().lower()
        if normalized_mode == "fast":
            return self.runtime_profile.fast_inference_mode or "global"
        if normalized_mode == "pro":
            if not self.runtime_profile.supports_concat:
                raise ValueError("当前模型档案不支持 Pro 检索。")
            return self.runtime_profile.pro_inference_mode or "global_detail"
        raise ValueError("search_mode 只能是 fast 或 pro。")

    def expected_feature_dim(self, search_mode: str) -> int:
        normalized_mode = str(search_mode or "fast").strip().lower()
        if normalized_mode == "pro":
            return int(self.runtime_profile.full_feature_dim)
        return int(self.runtime_profile.global_feature_dim)

    def extract_feature(self, image_path: str, search_mode: str = "fast"):
        if not self.initialized:
            self.setup()

        inference_mode = self.resolve_inference_mode(search_mode)
        expected_dim = self.expected_feature_dim(search_mode)

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)
        image_tensor = self.transforms(pil_image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            if hasattr(self.model, "inference") and hasattr(self.model, "preprocess_image"):
                images = self.model.preprocess_image(image_tensor)
                features = self.model.backbone(images)
                output = self.model.inference(features, inference_mode=inference_mode)
            else:
                if inference_mode != "global":
                    raise ValueError("当前模型结构不支持运行时切换到该推理模式。")
                output = self.model(image_tensor)

        feature_array = output.cpu().numpy() if torch.is_tensor(output) else output
        flat_feature = np.asarray(feature_array, dtype=np.float32).flatten()
        if flat_feature.size != expected_dim:
            raise ValueError(
                f"模型输出维度为 {flat_feature.size}，但模型档案期望 {expected_dim}。"
                "请检查模型档案中的特征维度和推理模式。"
            )
        return flat_feature


reid_engine = ReIDEngine()
