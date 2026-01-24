import os
import glob
from datetime import datetime  # 必须引入 datetime 用于转换
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.vehicle import VehicleFeature
from app.engine.predictor import reid_engine
from app.core.config import settings

GALLERY_DIR = os.path.join(settings.BASE_DIR, "../datasets/gallery")

def parse_filename(filename):
    """
    解析文件名
    输入: 0001_c001_20260124100000.jpg
    输出: 字典 (包含转换好的 datetime 对象)
    """
    try:
        # 去掉后缀
        name = os.path.splitext(filename)[0]
        parts = name.split('_')
        
        if len(parts) >= 3:
            time_str = parts[2]
            # 【关键修复】尝试将字符串解析为 datetime 对象
            # 格式: %Y(年) %m(月) %d(日) %H(时) %M(分) %S(秒)
            try:
                # 针对类似 "20260124100000" 的格式
                capture_dt = datetime.strptime(time_str, "%Y%m%d%H%M%S")
            except ValueError:
                # 如果格式不对 (比如只有日期 20260124)，尝试备用格式
                try:
                    capture_dt = datetime.strptime(time_str, "%Y%m%d")
                except:
                    # 如果实在解析不了，就用当前时间兜底，防止报错
                    capture_dt = datetime.now()

            return {
                "vehicle_id": parts[0],
                "cam_id": parts[1],
                "capture_time": capture_dt  # 返回真正的 datetime 对象
            }
        else:
            return {
                "vehicle_id": "unknown",
                "cam_id": "unknown",
                "capture_time": datetime.now() # 默认当前时间
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
    
    # 兼容 jpg, jpeg, png
    image_paths = glob.glob(os.path.join(GALLERY_DIR, "*.[jJ][pP][gG]")) + \
                  glob.glob(os.path.join(GALLERY_DIR, "*.[pP][nN][gG]")) + \
                  glob.glob(os.path.join(GALLERY_DIR, "*.[jJ][pP][eE][gG]"))
    
    print(f"📊 发现 {len(image_paths)} 张图片，准备入库...")
    
    count = 0
    try:
        for img_path in image_paths:
            filename = os.path.basename(img_path)
            
            # 查重逻辑
            exists = db.query(VehicleFeature).filter(
                VehicleFeature.img_path == f"gallery/{filename}"
            ).first()
            
            if exists:
                print(f"   ⏭️ 跳过已存在: {filename}")
                continue

            # 解析元数据
            meta = parse_filename(filename)
            
            # 提取特征
            vector_numpy = reid_engine.extract_feature(img_path)
            vector_blob = vector_numpy.tobytes()

            # 构建对象
            new_vehicle = VehicleFeature(
                vehicle_id=meta["vehicle_id"],
                cam_id=meta["cam_id"],
                capture_time=meta["capture_time"],  # 【关键修复】现在这里有值了
                img_path=f"gallery/{filename}",
                feature=vector_blob
            )
            
            db.add(new_vehicle)
            count += 1
            print(f"   ✅ 入库成功: {filename} -> {meta['capture_time']}")

        db.commit()
        print(f"🎉 同步完成！新增 {count} 条数据。")
        
    except Exception as e:
        print(f"❌ 入库失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_gallery_to_db()