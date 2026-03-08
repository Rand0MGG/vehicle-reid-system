import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import search, auth, admin_api
from app.engine.predictor import reid_engine

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

datasets_dir = os.path.join(settings.BASE_DIR, "../datasets")
if not os.path.exists(datasets_dir):
    os.makedirs(datasets_dir)
    
app.mount("/static", StaticFiles(directory=datasets_dir), name="static")

app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["auth"])
app.include_router(admin_api.router, prefix=settings.API_V1_STR + "/admin", tags=["admin"])

@app.on_event("startup")
async def startup_event():
    print("⏳ Initializing ReID Engine...")
    print(f"🚀 System works! API Docs: http://127.0.0.1:8000/docs")
    print(f"📂 Static Files served at: http://127.0.0.1:8000/static")

@app.get("/")
def read_root():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)