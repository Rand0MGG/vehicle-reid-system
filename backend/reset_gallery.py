# backend/reset_gallery.py
import sys
import os

# 路径修正，确保能导入 app
sys.path.append(os.getcwd())

from app.db.session import SessionLocal, engine
from app.models.vehicle import VehicleFeature
from sqlalchemy import text

def reset_table():
    db = SessionLocal()
    try:
        print("🗑️ 正在清空 vehicle_feature 表...")
        
        # 方法1: 使用 ORM 删除 (较慢，但通用)
        # db.query(VehicleFeature).delete()
        
        # 方法2: 直接执行 TRUNCATE (极快，且会重置 ID 自增计数器)
        # 注意: 根据数据库配置，可能需要 commit
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE vehicle_feature;"))
            # 如果是 SQLite 使用: DELETE FROM vehicle_feature;
            
        print("✅ 特征库已清空！所有数据已擦除。")
    except Exception as e:
        print(f"❌ 清空失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    response = input("⚠️ 警告: 这将删除所有已入库的车辆特征，确定吗？(y/n): ")
    if response.lower() == 'y':
        reset_table()
    else:
        print("已取消操作。")