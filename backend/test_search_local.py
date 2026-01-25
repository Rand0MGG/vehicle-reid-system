# backend/test_search_local.py
import sys
import os

# 把当前目录加入 Python 路径，防止找不到 app 包
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.services.search_service import SearchService

def test_logic():
    print("🧪 开始本地检索测试...")
    
    # 1. 准备 DB 会话
    db = SessionLocal()
    
    try:
        # 2. 实例化服务
        service = SearchService(db)
        
        # 3. 指定一张测试图片 (请确保这个路径下真的有张图，或者用 datasets/query 里的)
        # 如果没有 query 图片，随便找一张底库图片复制出来改名测试
        # 注意前面加了 "../" 跳出 backend 目录
        test_img_path = "../datasets/gallery/0001_c001_20260124100000.jpg"
        if not os.path.exists(test_img_path):
            print(f"❌ 找不到测试图片: {test_img_path}")
            print("💡 请修改 test_img_path 变量指向一张真实存在的图片！")
            return

        print(f"📸 查询图片: {test_img_path}")
        
        # 4. 调用核心方法
        results = service.search(test_img_path, top_k=3)
        
        # 5. 打印结果
        print(f"\n✅ 检索完成！找到 {len(results)} 个结果：")
        for i, res in enumerate(results):
            print(f"   [{i+1}] ID: {res['vehicle_id']} | 相似度: {res['score']:.4f} | 路径: {res['img_path']}")
            
            # 验证逻辑正确性：如果你搜的是底库里的原图，第一名相似度应该是 1.0 (或非常接近)
            # 注意：Mock 模式下相似度是随机的，这里主要看流程通不通
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_logic()