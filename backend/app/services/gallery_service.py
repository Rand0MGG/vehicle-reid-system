import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit_logger import execute_audit_insertion
from app.core.config import settings
from app.core.system_config import DEFAULT_ALLOWED_QUERY_SUFFIXES, load_system_config, save_system_config
from app.db.session import SessionLocal
from app.engine.predictor import reid_engine
from app.models.vehicle import VehicleFeature


logger = logging.getLogger(__name__)
gallery_dir = Path(settings.GALLERY_DIR).resolve()

sync_status = {
    "is_running": False,
    "logs": [],
}


def append_log(message: str) -> None:
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



def _persist_gallery_model_state(db: Session, current_model_file: str) -> None:
    total_records = db.query(VehicleFeature).count()
    save_system_config({"gallery_model_file": current_model_file if total_records > 0 else ""})



def clear_gallery_db(db: Session) -> None:
    try:
        db.execute(text("TRUNCATE TABLE vehicle_feature"))
        db.commit()
        save_system_config({"gallery_model_file": ""})
    except Exception:
        db.rollback()
        raise



def _collect_image_paths() -> list[Path]:
    allowed_suffixes = {
        suffix.lower()
        for suffix in load_system_config().get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
    }
    image_paths = []

    if not gallery_dir.exists():
        return image_paths

    for path in gallery_dir.iterdir():
        if path.is_file() and path.suffix.lower() in allowed_suffixes:
            image_paths.append(path)

    return sorted({path.resolve() for path in image_paths})


def open_gallery_folder() -> tuple[bool, str]:
    folder_path = str(gallery_dir)

    try:
        gallery_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(folder_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])

        return True, folder_path
    except Exception:
        logger.exception("Failed to open gallery directory: %s", folder_path)
        return False, folder_path



def run_sync_task(
    clear_existing: bool = False,
    actor_user_id: Optional[int] = None,
    action_label: str = "图库增量处理",
) -> None:
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
            execute_audit_insertion(actor_user_id, f"{action_label}失败：模型不一致", False)
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
        execute_audit_insertion(actor_user_id, f"{action_label}完成：新增 {count} 条记录", True)
    except Exception as exc:
        db.rollback()
        logger.exception("%s failed", action_label)
        append_log(f"图库处理被异常中断: {exc}")
        execute_audit_insertion(actor_user_id, f"{action_label}失败", False)
    finally:
        sync_status["is_running"] = False
        db.close()
