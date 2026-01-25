import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # 1. 引入静态文件处理
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import search
from app.engine.predictor import reid_engine

# 初始化 FastAPI 应用
app = FastAPI(title=settings.PROJECT_NAME)

# 配置跨域 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 挂载静态文件目录
# 让前端可以通过 http://localhost:8000/static/gallery/xxx.jpg 访问图片
# 我们挂载的是项目根目录下的 datasets 文件夹
datasets_dir = os.path.join(settings.BASE_DIR, "../datasets")
if not os.path.exists(datasets_dir):
    os.makedirs(datasets_dir) # 防止目录不存在报错
    
app.mount("/static", StaticFiles(directory=datasets_dir), name="static")

# 注册路由
app.include_router(search.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    print("⏳ Initializing ReID Engine...")
    # 预热引擎（可选，避免第一次请求太慢）
    # reid_engine.setup() 
    print(f"🚀 System works! API Docs: http://127.0.0.1:8000/docs")
    print(f"📂 Static Files served at: http://127.0.0.1:8000/static")

@app.get("/")
def read_root():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)