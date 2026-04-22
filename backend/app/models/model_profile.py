from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class ModelProfile(Base):
    """Administrator-maintained model profile visible in the product UI."""

    __tablename__ = "model_profile"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(80), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_public = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    active_revision_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    revisions = relationship(
        "ModelRevision",
        back_populates="profile",
        foreign_keys="ModelRevision.model_profile_id",
        cascade="save-update, merge",
    )

    @property
    def active_revision(self):
        for revision in self.revisions:
            if revision.id == self.active_revision_id:
                return revision
        return self.revisions[-1] if self.revisions else None


class ModelRevision(Base):
    """Immutable model configuration used to build and search feature vectors."""

    __tablename__ = "model_revision"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_profile_id = Column(Integer, ForeignKey("model_profile.id", ondelete="RESTRICT"), nullable=False, index=True)
    revision_name = Column(String(120), nullable=False)
    weights_file = Column(String(1024), nullable=False)
    config_file = Column(String(1024), nullable=False)
    supports_concat = Column(Boolean, nullable=False, default=False)
    supports_rerank = Column(Boolean, nullable=False, default=True)
    global_feature_dim = Column(Integer, nullable=False, default=2048)
    full_feature_dim = Column(Integer, nullable=False, default=2048)
    fast_inference_mode = Column(String(32), nullable=False, default="global")
    pro_inference_mode = Column(String(32), nullable=False, default="global_detail")
    signature = Column(String(40), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    profile = relationship(
        "ModelProfile",
        back_populates="revisions",
        foreign_keys=[model_profile_id],
    )
