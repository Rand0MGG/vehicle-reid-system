# backend/app/engine/predictor.py
import sys
import os
import cv2
import torch
import numpy as np
from PIL import Image  # 新增: 用于图像格式转换

# 1. 路径修复
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../fastreid"))

try:
    from fastreid.config import get_cfg
    from fastreid.modeling import build_model      # 直接构建模型
    from fastreid.utils.checkpoint import Checkpointer # 手动加载权重
    from fastreid.data.transforms import build_transforms # 手动构建预处理管线
    print("✅ FastReID 库加载成功")
except ImportError as e:
    print(f"❌ FastReID 加载失败: {e}")
    sys.exit(1)

from app.core.config import settings

class ReIDEngine:
    def __init__(self):
        self.model = None
        self.transforms = None
        self.device = None
        self.initialized = False

    def setup(self):
        """
        初始化模型、权重和预处理管线
        """
        if self.initialized:
            return

        print(f"⏳ 正在加载 AI 模型 (Manual Mode)...")
        
        # 1. 配置准备
        cfg = get_cfg()
        cfg.merge_from_file(settings.MODEL_CONFIG_FILE)
        cfg.MODEL.WEIGHTS = settings.MODEL_WEIGHTS_FILE
        cfg.MODEL.DEVICE = settings.DEVICE
        
        # 2. 构建模型结构
        self.model = build_model(cfg)
        self.model.eval() # 切换到评估模式
        
        # 3. 加载权重
        if os.path.exists(settings.MODEL_WEIGHTS_FILE):
            Checkpointer(self.model).load(settings.MODEL_WEIGHTS_FILE)
            print(f"   - 权重已加载: {settings.MODEL_WEIGHTS_FILE}")
        else:
            print(f"⚠️ 警告: 找不到权重文件，使用随机参数！")

        # 4. 构建预处理管线 (Resize -> ToTensor -> Normalize)
        # is_train=False 会自动应用测试集的预处理逻辑
        self.transforms = build_transforms(cfg, is_train=False)

        # 5. 设备设置
        self.device = torch.device(cfg.MODEL.DEVICE)
        self.model.to(self.device)
        
        self.initialized = True
        print("🚀 ReID 引擎加载完毕")

    def extract_feature(self, image_path: str):
        """
        输入: 图片路径
        输出: 2048维 Numpy 向量
        """
        if not self.initialized:
            self.setup()
            
        # 1. 读取图片 (OpenCV 读取的是 BGR 格式的 Numpy 数组)
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        # 2. 格式转换: BGR (OpenCV) -> RGB (PIL)
        # FastReID 的 transforms 通常期望 PIL Image 或 RGB 格式
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img)

        # 3. 预处理: PIL -> Tensor (C, H, W)
        # build_transforms 里包含了 ToTensor，所以这里出来就是 Tensor
        img_tensor = self.transforms(pil_img)

        # 4. 增加 Batch 维度: (C, H, W) -> (1, C, H, W)
        img_tensor = img_tensor.unsqueeze(0)
        
        # 5. 移动到指定设备 (CPU/GPU)
        img_tensor = img_tensor.to(self.device)

        # 6. 推理
        with torch.no_grad(): # 不计算梯度，节省内存
            # 模型输出通常就是特征向量
            features = self.model(img_tensor)

        # 7. 转回 Numpy
        if torch.is_tensor(features):
            feat = features.cpu().numpy()
        else:
            feat = features

        return feat.flatten()

# 单例导出
reid_engine = ReIDEngine()