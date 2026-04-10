from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, LargeBinary, String

from app.models.base import Base

class VehicleFeature(Base):
    """
    Python 对象映射：对应数据库里的 vehicle_feature 表
    """
    __tablename__ = "vehicle_feature"

    # 对应 SQL: id INT NOT NULL AUTO_INCREMENT
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 对应 SQL: vehicle_id VARCHAR(32)
    vehicle_id = Column(String(32), index=True, nullable=False)

    # 对应 SQL: cam_id VARCHAR(32)
    cam_id = Column(String(32), index=True, nullable=False)

    # 对应 SQL: capture_time DATETIME
    capture_time = Column(DateTime, index=True, nullable=True)

    # 对应 SQL: img_path VARCHAR(255)
    img_path = Column(String(255), nullable=False)

    # 对应 SQL: feature LONGBLOB
    # 注意：在 Python SQLAlchemy 中，LONGBLOB 对应 LargeBinary
    feature = Column(LargeBinary, nullable=False)

    # 对应 SQL: create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    create_time = Column(DateTime, default=datetime.now)
