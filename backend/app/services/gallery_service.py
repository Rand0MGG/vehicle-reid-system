import sys
import os

# ==========================================
# 🔧 关键修复：路径补丁
# 确保在任何目录下运行此脚本都能找到 'app' 模块
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前脚本所在目录 (services)
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) # 向上退三层找到 backend
sys.path.append(os.getcwd()) # 将当前运行命令的路径加入
# ==========================================

import glob
from datetime import datetime
from sqlalchemy.orm import Session

# 此时再导入 app 就不会报错了
from app.db.session import SessionLocal
from app.models.vehicle import VehicleFeature
from app.engine.predictor import reid_engine
from app.core.config import settings

GALLERY_DIR = os.path.join(settings.BASE_DIR, "../datasets/gallery")

def parse_filename(filename):
    """
    解析文件名
    输入: 0001_c001_20260124100000.jpg
    输出: 字典
    """
    try:
        # 去掉后缀
        name = os.path.splitext(filename)[0]
        parts = name.split('_')
        
        # VeRi-776 格式通常是: VehicleID_CameraID_FrameID.jpg
        # 例如: 0002_c002_00030600_0.jpg
        if len(parts) >= 2:
            vehicle_id = parts[0]
            cam_id = parts[1]
            
            # 尝试解析时间 (如果文件名里包含真实时间戳)
            # 对于 VeRi 这种只有帧号的，直接用当前时间兜底
            if len(parts) >= 3 and len(parts[2]) == 14:
                try:
                    capture_dt = datetime.strptime(parts[2], "%Y%m%d%H%M%S")
                except:
                    capture_dt = datetime.now()
            else:
                capture_dt = datetime.now()

            return {
                "vehicle_id": vehicle_id,
                "cam_id": cam_id,
                "capture_time": capture_dt
            }
        else:
            return {
                "vehicle_id": "unknown",
                "cam_id": "unknown",
                "capture_time": datetime.now()
            }
    except Exception as e:
        print(f"⚠️ 文件名解析警告: {filename} - {e}")
        return {
            "vehicle_id": "error", 
            "cam_id": "error", 
            "capture_time": datetime.now()
        }

def sync_gallery_to_db():
    db: Session = SessionLocal()
    print(f"📂 开始扫描底库目录: {GALLERY_DIR}")
    
    # 扫描所有常见的图片格式
    image_paths = glob.glob(os.path.join(GALLERY_DIR, "*.[jJ][pP][gG]")) + \
                  glob.glob(os.path.join(GALLERY_DIR, "*.[pP][nN][gG]")) + \
                  glob.glob(os.path.join(GALLERY_DIR, "*.[jJ][pP][eE][gG]"))
    
    print(f"📊 发现 {len(image_paths)} 张图片，准备入库...")
    
    count = 0
    try:
        for img_path in image_paths:
            filename = os.path.basename(img_path)
            
            # 1. 查重逻辑: 避免重复插入
            exists = db.query(VehicleFeature).filter(
                VehicleFeature.img_path == f"gallery/{filename}"
            ).first()
            
            if exists:
                # 即使存在，为了演示效果，可以选择不打印 "跳过"，或者只打印几个
                # print(f"   ⏭️ 跳过已存在: {filename}")
                continue

            # 2. 解析文件名元数据
            meta = parse_filename(filename)
            
            # 3. AI 引擎提取特征 (最耗时的一步)
            # ⚠️ 注意：如果你导入几百张图，这里可能会花几分钟
            vector_numpy = reid_engine.extract_feature(img_path)
            vector_blob = vector_numpy.tobytes()

            # 4. 构建数据库对象
            new_vehicle = VehicleFeature(
                vehicle_id=meta["vehicle_id"],
                cam_id=meta["cam_id"],
                capture_time=meta["capture_time"],
                img_path=f"gallery/{filename}",
                feature=vector_blob
            )
            
            db.add(new_vehicle)
            count += 1
            
            # 为了防止刷屏太快，每10张打印一次，或者实时打印
            print(f"   ✅ 入库成功 [{count}]: {filename}")

        db.commit()
        print(f"\n🎉 同步完成！共新增 {count} 条车辆数据。")
        
    except Exception as e:
        print(f"❌ 入库中断: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_gallery_to_db()