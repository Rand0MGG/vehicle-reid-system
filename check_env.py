import sys
import os
import torch

# 1. 自动挂载 fastreid 路径
root = os.path.dirname(os.path.abspath(__file__))
fastreid_path = os.path.join(root, "fastreid")

# 如果系统路径里没有 fastreid，就加进去
if fastreid_path not in sys.path:
    sys.path.append(fastreid_path)

print(f"正在检查路径: {fastreid_path}")

# 2. 尝试导入核心库
try:
    import fastreid
    from fastreid.config import get_cfg
    print("✅ FastReID 库导入成功！")
except ImportError as e:
    print("❌ FastReID 导入失败。")
    print(f"错误信息: {e}")
    sys.exit(1)

try:
    import detectron2
    print("✅ Detectron2 库导入成功！")
except ImportError:
    print("❌ Detectron2 导入失败。")

# 3. 检查 GPU
print("-" * 30)
if torch.cuda.is_available():
    print(f"✅ GPU 就绪: {torch.cuda.get_device_name(0)}")
else:
    print("⚠️  警告: 未检测到 GPU，将在 CPU 模式下运行。")

print("-" * 30)
print("环境配置完成！")