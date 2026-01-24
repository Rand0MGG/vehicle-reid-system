from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 1. 创建数据库引擎
# pool_pre_ping=True 可以在连接中断时自动重连
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI, 
    pool_pre_ping=True,
    echo=False  # 如果设为 True，控制台会打印所有 SQL 语句，方便调试
)

# 2. 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 依赖注入函数 (供 FastAPI 接口使用)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()