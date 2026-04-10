import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from PIL import Image

from app.core.config import settings
from app.core.system_config import load_system_config, save_system_config


FASTREID_ROOT = Path(__file__).resolve().parents[3] / "fastreid"
sys.path.append(str(FASTREID_ROOT))

try:
    from fastreid.config import get_cfg
    from fastreid.data.transforms import build_transforms
    from fastreid.modeling import build_model
    from fastreid.utils.checkpoint import Checkpointer

    print("FastReID 库加载成功")
except ImportError as exc:
    print(f"FastReID 加载失败: {exc}")
    sys.exit(1)


class ReIDEngine:
    def __init__(self):
        self.model = None
        self.transforms = None
        self.device = None
        self.initialized = False
        self.outputs_dir = Path(settings.BASE_DIR).joinpath("../outputs").resolve()

        runtime_config = load_system_config()
        configured_model = runtime_config.get("current_model_file") or settings.MODEL_WEIGHTS_FILE
        self.weights_file = self._resolve_weights_file(configured_model)

        saved_device = runtime_config.get("model_device", settings.DEVICE)
        if saved_device == "cuda" and not torch.cuda.is_available():
            saved_device = "cpu"
        self.device_name = saved_device

        if not runtime_config.get("current_model_file"):
            save_system_config({"current_model_file": self.get_current_weight_file()})

    def _resolve_weights_file(self, weights_file: Optional[str] = None) -> Path:
        if not weights_file:
            return self.weights_file.resolve()

        candidate = Path(weights_file)
        if not candidate.is_absolute():
            candidate = self.outputs_dir.joinpath(candidate)

        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.outputs_dir)
        except ValueError as exc:
            raise ValueError("模型权重文件必须位于 outputs 目录内。") from exc
        return resolved

    def list_weight_files(self):
        if not self.outputs_dir.exists():
            return []

        files = []
        for pattern in ("*.pth", "*.pt"):
            for file_path in self.outputs_dir.rglob(pattern):
                files.append(file_path.relative_to(self.outputs_dir).as_posix())
        return sorted(set(files))

    def get_current_weight_file(self):
        try:
            return self.weights_file.relative_to(self.outputs_dir).as_posix()
        except ValueError:
            return str(self.weights_file)

    def configure(self, weights_file: Optional[str] = None, device: Optional[str] = None, eager: bool = False):
        next_weights_file = self._resolve_weights_file(weights_file)
        next_device = device or self.device_name

        if next_device not in {"cpu", "cuda"}:
            raise ValueError("运行设备只能是 cpu 或 cuda。")
        if next_device == "cuda" and not torch.cuda.is_available():
            raise ValueError("当前环境不可用 CUDA。")

        self.weights_file = next_weights_file
        self.device_name = next_device
        self.reset()

        if eager:
            self.setup()

    def reset(self):
        self.model = None
        self.transforms = None
        self.device = None
        self.initialized = False

    def setup(self):
        if self.initialized:
            return

        print("正在加载 ReID 模型...")

        cfg = get_cfg()
        cfg.merge_from_file(settings.MODEL_CONFIG_FILE)
        cfg.MODEL.BACKBONE.PRETRAIN = False
        cfg.MODEL.WEIGHTS = str(self.weights_file)
        cfg.MODEL.DEVICE = self.device_name

        self.model = build_model(cfg)
        self.model.eval()

        if self.weights_file.exists():
            Checkpointer(self.model).load(str(self.weights_file))
            print(f"已加载模型权重: {self.weights_file}")
        else:
            print(f"未找到模型权重文件，将使用随机参数启动: {self.weights_file}")

        self.transforms = build_transforms(cfg, is_train=False)
        self.device = torch.device(cfg.MODEL.DEVICE)
        self.model.to(self.device)
        self.initialized = True
        print("ReID 引擎初始化完成")

    def extract_feature(self, image_path: str):
        if not self.initialized:
            self.setup()

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)
        image_tensor = self.transforms(pil_image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(image_tensor)

        if torch.is_tensor(features):
            feature_array = features.cpu().numpy()
        else:
            feature_array = features

        return np.asarray(feature_array).flatten()


reid_engine = ReIDEngine()
