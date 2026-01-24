import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
# 引入我们刚才写的接口文件
from app.api.endpoints import search
# 引入引擎，确保启动时能执行初始化
from app.engine.predictor import reid_engine

# 初始化 FastAPI 应用
app = FastAPI(title=settings.PROJECT_NAME)

# 配置跨域资源共享 (CORS)
# 允许你的 Vue 前端 (通常在端口 5173) 访问此后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由：把 search.py 里的接口挂载到 /api/v1 路径下
app.include_router(search.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """
    系统启动时的钩子函数
    """
    print("⏳ Initializing ReID Engine...")
    reid_engine.setup()
    print("🚀 System works! Backend is running at http://127.0.0.1:8000")

@app.get("/")
def read_root():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    # 启动服务器，开启 reload 模式（代码修改后自动重启）
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)