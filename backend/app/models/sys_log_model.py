from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.models.user import Base

class SysLog(Base):
    __tablename__ = "sys_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False)
    operation = Column(String(100), nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    exec_time = Column(DateTime, default=datetime.now)