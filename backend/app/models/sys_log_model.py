from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class SysLog(Base):
    __tablename__ = "sys_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True)
    operation = Column(String(100), nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    exec_time = Column(DateTime, nullable=False, default=datetime.now)
