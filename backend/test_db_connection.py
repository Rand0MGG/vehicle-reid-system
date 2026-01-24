from app.db.session import SessionLocal
from app.models.user import User
from sqlalchemy import text

def test_connection():
    print("🔌 正在尝试连接数据库...")
    try:
        db = SessionLocal()
        # 1. 测试物理连接
        db.execute(text("SELECT 1"))
        print("✅ 物理连接成功！")
        
        # 2. 测试查询数据
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            print(f"✅ ORM 查询成功！发现管理员: {user.username}, 角色: {user.role}")
        else:
            print("❌ 连接成功但未找到 admin 用户 (请检查数据库数据)")
            
        db.close()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("💡 提示: 请检查 config.py 里的密码是否正确")

if __name__ == "__main__":
    test_connection()