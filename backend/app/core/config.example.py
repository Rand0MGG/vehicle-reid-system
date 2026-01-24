# backend/app/core/config.example.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Vehicle ReID System"
    API_V1_STR: str = "/api/v1"
    
    # 获取项目根目录
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 模型相关配置
    MODEL_CONFIG_FILE: str = os.path.join(BASE_DIR, "../configs/vehicle_reid.yml")
    MODEL_WEIGHTS_FILE: str = os.path.join(BASE_DIR, "../outputs/model_final.pth")
    
    # 运算设备 (cpu 或 cuda)
    DEVICE: str = "cpu"

    # --- 数据库配置 (示例) ---
    # 格式: mysql+pymysql://用户名:密码@地址:端口/数据库名
    # 请在本地部署时，将此文件重命名为 config.py 并修改下方的密码
    SQLALCHEMY_DATABASE_URI: str = "mysql+pymysql://root:******@localhost:3306/vehicle_reid_db"

settings = Settings()