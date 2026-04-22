import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit_logger import execute_audit_insertion
from app.core.system_config import DEFAULT_ALLOWED_QUERY_SUFFIXES, load_system_config
from app.db.session import SessionLocal
from app.engine.predictor import reid_engine
from app.models.model_profile import ModelProfile, ModelRevision
from app.models.vehicle import Camera, FeatureBuildTask, GalleryFeature, GalleryImage, VehicleIdentity
from app.services.model_profile_service import get_active_revision, validate_revision_files


logger = logging.getLogger(__name__)

sync_status = {
    "is_running": False,
    "logs": [],
    "task_id": None,
    "model_profile_id": None,
    "model_revision_id": None,
    "task_type": "",
    "total": 0,
    "processed": 0,
    "created": 0,
    "skipped": 0,
    "failed": 0,
    "message": "",
}


def append_log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    sync_status["logs"].append(f"[{timestamp}] {message}")
    sync_status["logs"] = sync_status["logs"][-300:]


def start_gallery_operation(task_type: str, message: str) -> None:
    sync_status.update(
        {
            "is_running": True,
            "logs": [],
            "task_id": None,
            "model_profile_id": None,
            "model_revision_id": None,
            "task_type": task_type,
            "total": 0,
            "processed": 0,
            "created": 0,
            "skipped": 0,
            "failed": 0,
            "message": message,
        }
    )
    append_log(message)


def finish_gallery_operation(message: str) -> None:
    sync_status["message"] = message
    append_log(message)
    sync_status["is_running"] = False


def parse_filename(filename: str) -> dict:
    try:
        parts = Path(filename).stem.split("_")
        vehicle_id = parts[0] if len(parts) >= 1 and parts[0] else "unknown"
        cam_id = parts[1] if len(parts) >= 2 and parts[1] else "unknown"
        capture_time = None
        if len(parts) >= 3 and len(parts[2]) == 14:
            try:
                capture_time = datetime.strptime(parts[2], "%Y%m%d%H%M%S")
            except ValueError:
                capture_time = None
        return {"vehicle_id": vehicle_id, "cam_id": cam_id, "capture_time": capture_time}
    except Exception:
        return {"vehicle_id": "unknown", "cam_id": "unknown", "capture_time": None}


def _allowed_image_suffixes() -> set[str]:
    config = load_system_config()
    return {
        str(suffix).lower()
        for suffix in config.get("allowed_query_suffixes", DEFAULT_ALLOWED_QUERY_SUFFIXES)
    }


def _normalize_image_path(path_value: str) -> Path:
    path = Path(str(path_value or "").strip().strip("\"'"))
    if not path:
        raise ValueError("图片路径不能为空。")
    return path.expanduser().resolve()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_image_size(path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def _get_or_create_vehicle(db: Session, vehicle_code: str) -> VehicleIdentity:
    vehicle = db.query(VehicleIdentity).filter(VehicleIdentity.vehicle_code == vehicle_code).first()
    if vehicle:
        return vehicle
    vehicle = VehicleIdentity(vehicle_code=vehicle_code)
    db.add(vehicle)
    db.flush()
    return vehicle


def _get_or_create_camera(db: Session, camera_code: str) -> Camera:
    camera = db.query(Camera).filter(Camera.camera_code == camera_code).first()
    if camera:
        return camera
    camera = Camera(camera_code=camera_code)
    db.add(camera)
    db.flush()
    return camera


def register_image_path(db: Session, path_value: str, *, actor_user_id: Optional[int] = None) -> tuple[GalleryImage, bool]:
    image_path = _normalize_image_path(path_value)
    if not image_path.exists() or not image_path.is_file():
        raise ValueError(f"图片文件不存在：{image_path}")
    if image_path.suffix.lower() not in _allowed_image_suffixes():
        raise ValueError(f"不支持的图片格式：{image_path.suffix}")

    normalized = str(image_path)
    path_hash = _hash_text(normalized)
    existing = db.query(GalleryImage).filter(GalleryImage.img_path_hash == path_hash).first()
    if existing:
        if existing.img_path != normalized:
            raise ValueError("图片路径哈希冲突，请检查图片路径记录。")
        return existing, False

    metadata = parse_filename(image_path.name)
    vehicle = _get_or_create_vehicle(db, metadata["vehicle_id"])
    camera = _get_or_create_camera(db, metadata["cam_id"])
    width, height = _read_image_size(image_path)
    stat = image_path.stat()

    record = GalleryImage(
        vehicle_identity_id=vehicle.id,
        camera_id=camera.id,
        capture_time=metadata["capture_time"],
        img_path=normalized,
        img_path_hash=path_hash,
        file_hash=_hash_file(image_path),
        file_size=int(stat.st_size),
        width=width,
        height=height,
        created_by=actor_user_id,
    )
    db.add(record)
    db.flush()
    return record, True


def register_image_paths(db: Session, paths: list[str], *, actor_user_id: Optional[int] = None) -> dict:
    created = 0
    skipped = 0
    errors = []
    items = []
    for path_value in paths:
        try:
            image, is_created = register_image_path(db, path_value, actor_user_id=actor_user_id)
            created += 1 if is_created else 0
            skipped += 0 if is_created else 1
            items.append(serialize_gallery_image(image))
        except ValueError as exc:
            errors.append({"path": path_value, "message": str(exc)})
    return {"created": created, "skipped": skipped, "errors": errors, "items": items}


def _register_paths_with_status(paths: list[str], *, actor_user_id: Optional[int] = None) -> dict:
    db = SessionLocal()
    created = 0
    skipped = 0
    errors = []
    total = len(paths)
    sync_status["total"] = total
    sync_status["message"] = f"准备注册 {total} 张图片。"
    append_log(sync_status["message"])

    try:
        for index, path_value in enumerate(paths, start=1):
            try:
                _, is_created = register_image_path(db, path_value, actor_user_id=actor_user_id)
                db.commit()
                if is_created:
                    created += 1
                else:
                    skipped += 1
            except ValueError as exc:
                db.rollback()
                errors.append({"path": path_value, "message": str(exc)})

            sync_status["processed"] = index
            sync_status["created"] = created
            sync_status["skipped"] = skipped
            sync_status["failed"] = len(errors)
            sync_status["message"] = f"已处理 {index}/{total}，新增 {created}，跳过 {skipped}，失败 {len(errors)}。"

            if index == total or index % 50 == 0 or errors and len(errors) <= 5:
                append_log(sync_status["message"])

        return {"created": created, "skipped": skipped, "errors": errors}
    finally:
        db.close()


def run_register_files_task(paths: list[str], actor_user_id: Optional[int] = None) -> None:
    if not sync_status["is_running"]:
        start_gallery_operation("register_files", "开始注册图片文件。")

    try:
        result = _register_paths_with_status(paths, actor_user_id=actor_user_id)
        ok = len(result["errors"]) == 0
        finish_gallery_operation(
            f"图片注册完成：新增 {result['created']}，跳过 {result['skipped']}，失败 {len(result['errors'])}。"
        )
        execute_audit_insertion(
            actor_user_id,
            f"注册图库图片：新增 {result['created']}，跳过 {result['skipped']}，失败 {len(result['errors'])}",
            ok,
        )
    except Exception as exc:
        logger.exception("Gallery file registration failed")
        finish_gallery_operation(f"图片注册失败：{exc}")
        execute_audit_insertion(actor_user_id, "注册图库图片失败", False)


def run_register_folder_task(folder_path: str, recursive: bool = True, actor_user_id: Optional[int] = None) -> None:
    if not sync_status["is_running"]:
        start_gallery_operation("register_folder", "开始注册目录图片。")

    try:
        append_log(f"正在扫描目录：{folder_path}")
        paths = collect_folder_images(folder_path, recursive=recursive)
        result = _register_paths_with_status(paths, actor_user_id=actor_user_id)
        ok = len(result["errors"]) == 0
        finish_gallery_operation(
            f"目录注册完成：新增 {result['created']}，跳过 {result['skipped']}，失败 {len(result['errors'])}。"
        )
        execute_audit_insertion(
            actor_user_id,
            f"注册图库目录：新增 {result['created']}，跳过 {result['skipped']}，失败 {len(result['errors'])}",
            ok,
        )
    except Exception as exc:
        logger.exception("Gallery folder registration failed")
        finish_gallery_operation(f"目录注册失败：{exc}")
        execute_audit_insertion(actor_user_id, "注册图库目录失败", False)


def collect_folder_images(folder_path: str, *, recursive: bool = True) -> list[str]:
    folder = Path(str(folder_path or "").strip().strip("\"'")).expanduser().resolve()
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"图片目录不存在：{folder}")
    suffixes = _allowed_image_suffixes()
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(str(path.resolve()) for path in iterator if path.is_file() and path.suffix.lower() in suffixes)


def serialize_gallery_image(image: GalleryImage) -> dict:
    return {
        "id": image.id,
        "vehicle_id": image.vehicle_id,
        "cam_id": image.cam_id,
        "capture_time": image.capture_time,
        "img_path": image.img_path,
        "img_path_hash": image.img_path_hash,
        "file_hash": image.file_hash,
        "file_size": image.file_size,
        "width": image.width,
        "height": image.height,
        "created_by": image.created_by,
        "created_at": image.created_at,
        "updated_at": image.updated_at,
        "feature_count": len(image.features) if image.features is not None else 0,
    }


def list_gallery_images(db: Session, *, page: int = 1, size: int = 20) -> dict:
    page = max(1, int(page))
    size = max(1, min(200, int(size)))
    query = (
        db.query(GalleryImage)
        .options(
            joinedload(GalleryImage.vehicle_identity),
            joinedload(GalleryImage.camera),
            joinedload(GalleryImage.features),
        )
        .order_by(GalleryImage.id.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": [serialize_gallery_image(item) for item in items]}


def delete_gallery_image(db: Session, image_id: int) -> None:
    image = db.query(GalleryImage).filter(GalleryImage.id == image_id).first()
    if not image:
        raise ValueError("图片记录不存在。")
    feature_count = db.query(func.count(GalleryFeature.id)).filter(GalleryFeature.image_id == image_id).scalar() or 0
    if feature_count > 0:
        raise ValueError("该图片已被模型特征引用，不能删除。")
    db.delete(image)


def clear_features_for_revision(db: Session, revision_id: int) -> int:
    count = db.query(GalleryFeature).filter(GalleryFeature.model_revision_id == revision_id).count()
    db.query(GalleryFeature).filter(GalleryFeature.model_revision_id == revision_id).delete(synchronize_session=False)
    return int(count)


def create_build_task(db: Session, revision: ModelRevision, *, actor_user_id: Optional[int], rebuild: bool) -> FeatureBuildTask:
    task = FeatureBuildTask(
        model_revision_id=revision.id,
        triggered_by=actor_user_id,
        mode="rebuild" if rebuild else "incremental",
        status="pending",
        message="等待开始",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_feature_build_task(
    task_id: int,
    actor_user_id: Optional[int] = None,
) -> None:
    if sync_status["is_running"]:
        return

    db = SessionLocal()
    start_gallery_operation("feature_build", "开始构建模型图库特征。")
    sync_status["task_id"] = task_id

    try:
        task = db.query(FeatureBuildTask).filter(FeatureBuildTask.id == task_id).first()
        if not task:
            append_log("任务记录不存在。")
            return

        revision = db.query(ModelRevision).filter(ModelRevision.id == task.model_revision_id).first()
        if not revision:
            raise ValueError("模型版本不存在。")

        profile = db.query(ModelProfile).filter(ModelProfile.id == revision.model_profile_id).first()
        task.status = "running"
        task.started_at = datetime.now()
        task.message = "正在构建图库特征"
        db.commit()

        sync_status["model_profile_id"] = revision.model_profile_id
        sync_status["model_revision_id"] = revision.id
        append_log(f"开始构建模型特征：{profile.name if profile else revision.revision_name}")

        validate_revision_files(revision, require_exists=True)
        reid_engine.configure(profile=revision, eager=reid_engine.initialized)

        if task.mode == "rebuild":
            removed = clear_features_for_revision(db, revision.id)
            db.commit()
            append_log(f"已清空该模型版本旧特征 {removed} 条。")

        query = (
            db.query(GalleryImage)
            .options(joinedload(GalleryImage.features))
            .order_by(GalleryImage.id.asc())
        )
        images = query.all()
        existing_image_ids = {
            item[0]
            for item in db.query(GalleryFeature.image_id)
            .filter(GalleryFeature.model_revision_id == revision.id)
            .all()
        }
        pending_images = [image for image in images if image.id not in existing_image_ids]
        task.total_images = len(pending_images)
        db.commit()
        append_log(f"待处理图片 {len(pending_images)} 张。")

        search_mode = "pro" if revision.supports_concat else "fast"
        expected_dim = int(revision.full_feature_dim)
        for image in pending_images:
            task.processed_images += 1
            try:
                vector = reid_engine.extract_feature(image.img_path, search_mode=search_mode)
                if vector.size != expected_dim:
                    raise ValueError(f"特征维度为 {vector.size}，模型版本期望 {expected_dim}。")

                db.add(
                    GalleryFeature(
                        image_id=image.id,
                        model_revision_id=revision.id,
                        feature=vector.astype("float32", copy=False).tobytes(),
                    )
                )
                task.success_count += 1
                task.message = f"已处理 {task.processed_images}/{task.total_images}"
                append_log(f"已完成 [{task.processed_images}/{task.total_images}] {Path(image.img_path).name}")
                db.commit()
            except Exception as exc:
                db.rollback()
                task = db.query(FeatureBuildTask).filter(FeatureBuildTask.id == task_id).first()
                task.processed_images += 1
                task.failed_count += 1
                task.message = f"{Path(image.img_path).name}: {exc}"
                append_log(f"失败：{Path(image.img_path).name}，{exc}")
                db.commit()

        task.status = "succeeded" if task.failed_count == 0 else "failed"
        task.finished_at = datetime.now()
        task.message = f"完成：成功 {task.success_count}，失败 {task.failed_count}"
        db.commit()
        append_log(task.message)
        execute_audit_insertion(actor_user_id, f"构建模型图库特征：成功 {task.success_count}，失败 {task.failed_count}", task.failed_count == 0)
    except Exception as exc:
        db.rollback()
        logger.exception("Feature build task failed")
        task = db.query(FeatureBuildTask).filter(FeatureBuildTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.finished_at = datetime.now()
            task.message = str(exc)
            db.commit()
        append_log(f"图库特征构建被异常中断：{exc}")
        execute_audit_insertion(actor_user_id, "构建模型图库特征失败", False)
    finally:
        sync_status["is_running"] = False
        db.close()


def get_revision_feature_status(db: Session, revision: ModelRevision) -> dict:
    image_count = db.query(func.count(GalleryImage.id)).scalar() or 0
    feature_count = (
        db.query(func.count(GalleryFeature.id))
        .filter(GalleryFeature.model_revision_id == revision.id)
        .scalar()
        or 0
    )
    latest_task = (
        db.query(FeatureBuildTask)
        .filter(FeatureBuildTask.model_revision_id == revision.id)
        .order_by(FeatureBuildTask.id.desc())
        .first()
    )
    return {
        "image_count": int(image_count),
        "feature_count": int(feature_count),
        "missing_count": max(0, int(image_count) - int(feature_count)),
        "is_complete": int(image_count) > 0 and int(feature_count) >= int(image_count),
        "latest_task": serialize_build_task(latest_task),
    }


def serialize_build_task(task: Optional[FeatureBuildTask]) -> Optional[dict]:
    if task is None:
        return None
    return {
        "id": task.id,
        "model_revision_id": task.model_revision_id,
        "triggered_by": task.triggered_by,
        "mode": task.mode,
        "status": task.status,
        "total_images": task.total_images,
        "processed_images": task.processed_images,
        "success_count": task.success_count,
        "failed_count": task.failed_count,
        "message": task.message or "",
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }
