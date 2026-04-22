from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.models.base import Base


class SystemConfig(Base):
    """Database representation for system-level settings."""

    __tablename__ = "system_config"

    config_key = Column(String(80), primary_key=True)
    config_value = Column(Text, nullable=True)
    value_type = Column(String(20), nullable=False, default="string")
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
