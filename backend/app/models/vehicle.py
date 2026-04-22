from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class VehicleIdentity(Base):
    """Normalized vehicle label parsed from registered image paths."""

    __tablename__ = "vehicle_identity"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_code = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    images = relationship("GalleryImage", back_populates="vehicle_identity")


class Camera(Base):
    """Normalized camera label parsed from registered image paths."""

    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_code = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    images = relationship("GalleryImage", back_populates="camera")


class GalleryImage(Base):
    """Registered gallery image. The database stores metadata and path only."""

    __tablename__ = "gallery_image"
    __table_args__ = (UniqueConstraint("img_path_hash", name="uk_gallery_image_path_hash"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_identity_id = Column(Integer, ForeignKey("vehicle_identity.id", ondelete="RESTRICT"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False, index=True)
    capture_time = Column(DateTime, nullable=True, index=True)
    img_path = Column(String(1024), nullable=False)
    img_path_hash = Column(String(64), nullable=False)
    file_hash = Column(String(40), nullable=True, index=True)
    file_size = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    vehicle_identity = relationship("VehicleIdentity", back_populates="images")
    camera = relationship("Camera", back_populates="images")
    features = relationship("GalleryFeature", back_populates="image", cascade="save-update, merge")

    @property
    def vehicle_id(self) -> str:
        return self.vehicle_identity.vehicle_code if self.vehicle_identity else "unknown"

    @property
    def cam_id(self) -> str:
        return self.camera.camera_code if self.camera else "unknown"


class GalleryFeature(Base):
    """One full feature vector per gallery image and model revision."""

    __tablename__ = "gallery_feature"
    __table_args__ = (UniqueConstraint("image_id", "model_revision_id", name="uk_gallery_feature_image_revision"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("gallery_image.id", ondelete="RESTRICT"), nullable=False, index=True)
    model_revision_id = Column(Integer, ForeignKey("model_revision.id", ondelete="RESTRICT"), nullable=False, index=True)
    feature = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    image = relationship("GalleryImage", back_populates="features")
    model_revision = relationship("ModelRevision")


class FeatureBuildTask(Base):
    """Tracks per-model gallery feature extraction work."""

    __tablename__ = "feature_build_task"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_revision_id = Column(Integer, ForeignKey("model_revision.id", ondelete="RESTRICT"), nullable=False, index=True)
    triggered_by = Column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True)
    mode = Column(String(20), nullable=False, default="incremental")
    status = Column(String(20), nullable=False, default="pending", index=True)
    total_images = Column(Integer, nullable=False, default=0)
    processed_images = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    model_revision = relationship("ModelRevision")
