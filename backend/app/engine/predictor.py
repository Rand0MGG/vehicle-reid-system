import sys
import os
import numpy as np

# 【核心修复】将路径指向 fastreid 代码仓库的根目录
# 原来是指向 E:\reid，现在指向 E:\reid\fastreid
# 这样 Python 搜索路径里包含了外层目录，import fastreid 时就能找到内层的包了
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../fastreid"))

try:
    # 尝试导入 fastreid，验证环境是否配置正确
    from fastreid.config import get_cfg
    from fastreid.engine import DefaultPredictor
    print("✅ FastReID library loaded successfully!")
except ImportError as e:
    print(f"❌ Failed to load FastReID: {e}")
    # 为了防止路径错误导致程序直接崩溃无法调试，这里暂时 pass
    pass

class ReIDEngine:
    def __init__(self):
        self.predictor = None
        print("🤖 ReID Engine initialized (Mock Mode)")

    def setup(self):
        """
        将来在这里加载 .pth 权重文件
        """
        pass

    def extract_feature(self, image_path: str):
        """
        暂时模拟特征提取，返回一个随机向量，证明流程跑通
        """
        # TODO: 后续接入真实的 FastReID 推理: feat = self.predictor(img)
        
        # 模拟返回一个 2048 维的特征向量
        fake_feature = np.random.rand(2048).astype(np.float32)
        return fake_feature

# 单例模式，全局只初始化一次
reid_engine = ReIDEngine()