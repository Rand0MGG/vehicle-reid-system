import sys
import os
sys.path.append(os.getcwd())
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def init_db():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        hashed_password = get_password_hash("123456")
        db_user = User(username="admin", password=hashed_password, role="admin")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print("系统管理员账号创建完毕")
    else:
        print("系统管理员账号已存在")
    db.close()

if __name__ == "__main__":
    init_db()