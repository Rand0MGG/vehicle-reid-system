import logging

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine
from app.models.base import Base

# Import models so SQLAlchemy metadata knows every table.
from app.models.model_profile import ModelProfile, ModelRevision  # noqa: F401
from app.models.sys_log_model import SysLog  # noqa: F401
from app.models.system_config_model import SystemConfig  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vehicle import Camera, FeatureBuildTask, GalleryFeature, GalleryImage, VehicleIdentity  # noqa: F401


logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = {
    "model_profile": {
        "id",
        "name",
        "description",
        "is_enabled",
        "is_public",
        "display_order",
        "active_revision_id",
        "created_at",
        "updated_at",
    },
    "model_revision": {
        "id",
        "model_profile_id",
        "revision_name",
        "weights_file",
        "config_file",
        "supports_concat",
        "supports_rerank",
        "global_feature_dim",
        "full_feature_dim",
        "fast_inference_mode",
        "pro_inference_mode",
        "signature",
        "created_at",
    },
    "gallery_image": {
        "id",
        "vehicle_identity_id",
        "camera_id",
        "capture_time",
        "img_path",
        "img_path_hash",
        "file_hash",
        "file_size",
        "width",
        "height",
        "created_by",
        "created_at",
        "updated_at",
    },
    "gallery_feature": {
        "id",
        "image_id",
        "model_revision_id",
        "feature",
        "created_at",
        "updated_at",
    },
    "feature_build_task": {
        "id",
        "model_revision_id",
        "triggered_by",
        "mode",
        "status",
        "total_images",
        "processed_images",
        "success_count",
        "failed_count",
        "message",
        "created_at",
        "started_at",
        "finished_at",
    },
}


DROP_GROUPS = {
    "model": ("feature_build_task", "gallery_feature", "model_revision", "model_profile"),
    "gallery": ("feature_build_task", "gallery_feature", "gallery_image", "camera", "vehicle_identity"),
    "legacy": ("vehicle_feature",),
}


def _table_columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _is_incompatible(inspector, table_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    required = REQUIRED_COLUMNS.get(table_name, set())
    return not required.issubset(_table_columns(inspector, table_name))


def _drop_tables(conn, table_names: tuple[str, ...]) -> None:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    try:
        for table_name in table_names:
            conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
            logger.warning("Dropped incompatible table: %s", table_name)
    finally:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def find_incompatible_tables() -> list[str]:
    incompatible: list[str] = []
    with engine.begin() as conn:
        inspector = inspect(conn)

        if inspector.has_table("vehicle_feature"):
            incompatible.extend(
                table_name
                for table_name in DROP_GROUPS["legacy"]
                if inspector.has_table(table_name)
            )

        if any(_is_incompatible(inspector, table) for table in ("model_profile", "model_revision")):
            incompatible.extend(
                table_name
                for table_name in DROP_GROUPS["model"]
                if inspector.has_table(table_name)
            )
            inspector = inspect(conn)

        if any(_is_incompatible(inspector, table) for table in ("gallery_image", "gallery_feature", "feature_build_task")):
            incompatible.extend(
                table_name
                for table_name in DROP_GROUPS["gallery"]
                if inspector.has_table(table_name)
            )

    return sorted(set(incompatible))


def drop_incompatible_development_tables() -> None:
    """Drop old development tables that cannot safely run with the new schema.

    User, log, and system config tables are intentionally preserved. Model and
    gallery feature data from older schemas are discarded instead of being
    adapted into the new 3NF design.
    """

    with engine.begin() as conn:
        inspector = inspect(conn)

        if inspector.has_table("vehicle_feature"):
            _drop_tables(conn, DROP_GROUPS["legacy"])
            inspector = inspect(conn)

        if any(_is_incompatible(inspector, table) for table in ("model_profile", "model_revision")):
            _drop_tables(conn, DROP_GROUPS["model"])
            inspector = inspect(conn)

        if any(_is_incompatible(inspector, table) for table in ("gallery_image", "gallery_feature", "feature_build_task")):
            _drop_tables(conn, DROP_GROUPS["gallery"])


def run_startup_migrations() -> None:
    """Create the current database structure without seeding users."""

    incompatible_tables = find_incompatible_tables()
    if incompatible_tables:
        if settings.ALLOW_DESTRUCTIVE_STARTUP_MIGRATIONS:
            logger.warning(
                "ALLOW_DESTRUCTIVE_STARTUP_MIGRATIONS is enabled; dropping incompatible tables: %s",
                ", ".join(incompatible_tables),
            )
            drop_incompatible_development_tables()
        else:
            joined = ", ".join(incompatible_tables)
            raise RuntimeError(
                "Incompatible database schema detected for tables: "
                f"{joined}. Refusing to drop tables automatically. "
                "If this is an intentional development reset, set "
                "ALLOW_DESTRUCTIVE_STARTUP_MIGRATIONS=true and restart."
            )
    Base.metadata.create_all(bind=engine)
    logger.info("Database structure checked")
