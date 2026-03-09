import glob
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.vehicle import VehicleFeature
from app.engine.predictor import reid_engine
from app.core.config import settings

gallery_dir = os.path.join(settings.BASE_DIR, "../datasets/gallery")

sync_status = {
    "is_running": False,
    "logs": []
}

def append_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    sync_status["logs"].append(f"[{timestamp}] {msg}")

def parse_filename(filename):
    try:
        name = os.path.splitext(filename)[0]
        parts = name.split('_')
        if len(parts) >= 2:
            vehicle_id = parts[0]
            cam_id = parts[1]
            if len(parts) >= 3 and len(parts[2]) == 14:
                try:
                    capture_dt = datetime.strptime(parts[2], "%Y%m%d%H%M%S")
                except:
                    capture_dt = datetime.now()
            else:
                capture_dt = datetime.now()
            return {"vehicle_id": vehicle_id, "cam_id": cam_id, "capture_time": capture_dt}
        else:
            return {"vehicle_id": "unknown", "cam_id": "unknown", "capture_time": datetime.now()}
    except Exception as e:
        return {"vehicle_id": "error", "cam_id": "error", "capture_time": datetime.now()}

def clear_gallery_db(db: Session):
    try:
        db.execute(text("TRUNCATE TABLE vehicle_feature"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

def run_sync_task(db: Session):
    if sync_status["is_running"]:
        return
    
    sync_status["is_running"] = True
    sync_status["logs"].clear()
    append_log(f"开始扫描底库目录: {gallery_dir}")
    
    try:
        image_paths = glob.glob(os.path.join(gallery_dir, "*.[jJ][pP][gG]")) + \
                      glob.glob(os.path.join(gallery_dir, "*.[pP][nN][gG]")) + \
                      glob.glob(os.path.join(gallery_dir, "*.[jJ][pP][eE][gG]"))
        
        append_log(f"发现 {len(image_paths)} 张图像，准备执行高维特征提取")
        
        count = 0
        for img_path in image_paths:
            filename = os.path.basename(img_path)
            exists = db.query(VehicleFeature).filter(
                VehicleFeature.img_path == f"gallery/{filename}"
            ).first()
            
            if exists:
                continue

            meta = parse_filename(filename)
            vector_numpy = reid_engine.extract_feature(img_path)
            vector_blob = vector_numpy.tobytes()

            new_vehicle = VehicleFeature(
                vehicle_id=meta["vehicle_id"],
                cam_id=meta["cam_id"],
                capture_time=meta["capture_time"],
                img_path=f"gallery/{filename}",
                feature=vector_blob
            )
            
            db.add(new_vehicle)
            count += 1
            append_log(f"底层落盘成功 [{count}]: {filename}")

        db.commit()
        append_log(f"同步指令执行完毕，共持久化 {count} 条车辆记录")
    except Exception as e:
        db.rollback()
        append_log(f"提取管线异常中断: {str(e)}")
    finally:
        sync_status["is_running"] = False
        db.close()