import sys
import os
from sqlalchemy import text

# 确保能找到 app 模块
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.vehicle import VehicleFeature
from app.models.user import User  # 【新增】引入用户模型

def inspect_data():
    session = SessionLocal()
    try:
        # ==========================================
        # 1. 检查 User 表 (sys_user)
        # ==========================================
        print("\n" + "="*50)
        print("👤 正在查询 sys_user 表...")
        print("="*50)
        
        users = session.query(User).all()
        
        if not users:
            print("⚠️ User 表是空的！")
        else:
            print(f"📊 共发现 {len(users)} 个用户：")
            print("-" * 60)
            # 打印表头
            print(f"{'ID':<5} | {'Username':<15} | {'Role':<10} | {'Create Time'}")
            print("-" * 60)

            for u in users:
                create_time = u.create_time.strftime("%Y-%m-%d %H:%M") if u.create_time else "N/A"
                print(f"{u.id:<5} | {u.username:<15} | {u.role:<10} | {create_time}")

        # ==========================================
        # 2. 检查 VehicleFeature 表 (vehicle_feature)
        # ==========================================
        print("\n" + "="*50)
        print("🚗 正在查询 vehicle_feature 表...")
        print("="*50)
        
        records = session.query(VehicleFeature).all()
        
        if not records:
            print("⚠️ VehicleFeature 表是空的！")
        else:
            print(f"📊 共发现 {len(records)} 条车辆记录：")
            print("-" * 90)
            # 打印表头
            print(f"{'ID':<5} | {'Vehicle ID':<12} | {'Cam ID':<8} | {'Time':<20} | {'Img Path'}")
            print("-" * 90)

            for r in records:
                # 这里我们不再打印 Feature Size，以免产生误解
                # 而是打印图片路径，这样更直观
                time_str = r.capture_time.strftime("%Y-%m-%d %H:%M:%S") if r.capture_time else "None"
                # 截取路径后半段显示，防止太长
                short_path = r.img_path  # 不截断，直接显示全名
                
                print(f"{r.id:<5} | {r.vehicle_id:<12} | {r.cam_id:<8} | {time_str:<20} | {short_path}")
        
        print("\n✅ 所有表检查完毕。")

    except Exception as e:
        print(f"❌ 查询出错: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_data()