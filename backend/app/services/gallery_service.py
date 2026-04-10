from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.system_config import load_system_config, save_system_config
from app.db.session import SessionLocal
from app.engine.predictor import reid_engine
from app.models.vehicle import VehicleFeature


gallery_dir = Path(settings.BASE_DIR).joinpath("../datasets/gallery").resolve()

sync_status = {
    "is_running": False,
    "logs": [],
}


def append_log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    sync_status["logs"].append(f"[{timestamp}] {message}")



def parse_filename(filename):
    try:
        parts = Path(filename).stem.split("_")
        if len(parts) < 2:
            return {"vehicle_id": "unknown", "cam_id": "unknown", "capture_time": datetime.now()}

        vehicle_id = parts[0]
        cam_id = parts[1]
        capture_time = datetime.now()

        if len(parts) >= 3 and len(parts[2]) == 14:
            try:
                capture_time = datetime.strptime(parts[2], "%Y%m%d%H%M%S")
            except ValueError:
                capture_time = datetime.now()

        return {"vehicle_id": vehicle_id, "cam_id": cam_id, "capture_time": capture_time}
    except Exception:
        return {"vehicle_id": "error", "cam_id": "error", "capture_time": datetime.now()}



def _persist_gallery_model_state(db: Session, current_model_file: str):
    total_records = db.query(VehicleFeature).count()
    save_system_config({"gallery_model_file": current_model_file if total_records > 0 else ""})



def clear_gallery_db(db: Session):
    try:
        db.execute(text("TRUNCATE TABLE vehicle_feature"))
        db.commit()
        save_system_config({"gallery_model_file": ""})
    except Exception:
        db.rollback()
        raise



def _collect_image_paths():
    image_paths = []
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
        image_paths.extend(gallery_dir.glob(pattern))
    return sorted({path.resolve() for path in image_paths})



def run_sync_task(clear_existing: bool = False):
    if sync_status["is_running"]:
        return

    db = SessionLocal()
    sync_status["is_running"] = True
    sync_status["logs"].clear()
    append_log(f"开始扫描图库目录: {gallery_dir}")

    try:
        current_model_file = reid_engine.get_current_weight_file()
        gallery_model_file = load_system_config().get("gallery_model_file", "")

        if not clear_existing and gallery_model_file and gallery_model_file != current_model_file:
            append_log("当前模型与图库特征使用的模型不一致，请先重新处理全部图片。")
            return

        if clear_existing:
            clear_gallery_db(db)
            append_log("已清空现有特征记录，开始重新处理全部图片。")

        image_paths = _collect_image_paths()
        append_log(f"发现 {len(image_paths)} 张图片，准备提取特征。")

        count = 0
        for image_path in image_paths:
            filename = image_path.name
            existing_record = db.query(VehicleFeature).filter(
                VehicleFeature.img_path == f"gallery/{filename}"
            ).first()

            if existing_record:
                continue

            metadata = parse_filename(filename)
            vector_numpy = reid_engine.extract_feature(str(image_path))
            vector_blob = vector_numpy.tobytes()

            db.add(
                VehicleFeature(
                    vehicle_id=metadata["vehicle_id"],
                    cam_id=metadata["cam_id"],
                    capture_time=metadata["capture_time"],
                    img_path=f"gallery/{filename}",
                    feature=vector_blob,
                )
            )
            count += 1
            append_log(f"已完成特征提取 [{count}]: {filename}")

        db.commit()
        _persist_gallery_model_state(db, current_model_file)
        append_log(f"图库处理完成，本次新增 {count} 条特征记录。")
    except Exception as exc:
        db.rollback()
        append_log(f"图库处理被异常中断: {exc}")
    finally:
        sync_status["is_running"] = False
        db.close()
