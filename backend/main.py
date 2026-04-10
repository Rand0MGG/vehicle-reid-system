import collections
import logging
from pathlib import Path

from app.core.logging_config import configure_logging
from app.core.system_config import load_system_config

configure_logging(load_system_config().get("log_level", "INFO"))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import admin_api, auth, search
from app.core.config import settings
from app.db.bootstrap import run_startup_migrations


logger = logging.getLogger(__name__)


if not hasattr(collections, "Mapping"):
    import collections.abc

    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, "Iterable"):
    import collections.abc

    collections.Iterable = collections.abc.Iterable


app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

datasets_dir = Path(settings.DATASETS_DIR).resolve()
datasets_dir.mkdir(parents=True, exist_ok=True)
Path(settings.SEARCH_UPLOAD_DIR).resolve().mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(datasets_dir)), name="static")

app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["auth"])
app.include_router(admin_api.router, prefix=settings.API_V1_STR + "/admin", tags=["admin"])


@app.on_event("startup")
async def startup_event():
    run_startup_migrations()
    logger.info("API docs available at: http://127.0.0.1:8000/docs")
    logger.info("Static files available at: http://127.0.0.1:8000/static")


@app.get("/")
def read_root():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
