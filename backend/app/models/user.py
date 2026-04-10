from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.models.base import Base

class User(Base):
    # 对应数据库里的表名
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(20), default="user")
    is_builtin = Column(Boolean, default=False, nullable=False)
    create_time = Column(DateTime, default=datetime.now)
