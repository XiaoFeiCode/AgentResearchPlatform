"""FastAPI main application — primary backend."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.services.forum_service import init_forum_log, shutdown_forum_service
from app.utils.forum_reader import init_forum_reader, shutdown_forum_reader
from app.routers import system, config, forum, search, events, report


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    events.init_event_stream()
    init_forum_log()
    init_forum_reader()
    logger.info("FastAPI 服务器已启动，共享服务已初始化")
    try:
        yield
    finally:
        shutdown_forum_reader()
        shutdown_forum_service()
        events.shutdown_event_stream()
        logger.info("FastAPI 服务器已关闭，共享服务已清理")


app = FastAPI(
    title="多源舆情智能分析系统 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(system.router)
app.include_router(system.app_status_router)
app.include_router(config.router)
app.include_router(forum.router)
app.include_router(search.router)
app.include_router(events.router)
app.include_router(report.router)

# ── SPA & static files ──────────────────────────────────────────────────

_BASE = Path(__file__).resolve().parent.parent
_VUE_DIST = _BASE / "frontend" / "dist"
_INDEX_HTML = _VUE_DIST / "index.html"


# Static files from Vue build
if (_VUE_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_VUE_DIST / "assets"), name="vue_assets")


@app.get("/favicon.svg")
async def serve_favicon():
    path = _VUE_DIST / "favicon.svg"
    if path.exists():
        return FileResponse(path)
    return Response(status_code=404)


@app.get("/icons.svg")
async def serve_icons():
    path = _VUE_DIST / "icons.svg"
    if path.exists():
        return FileResponse(path)
    return Response(status_code=404)


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve Vue SPA entry point."""
    if _INDEX_HTML.exists():
        return FileResponse(_INDEX_HTML)
    return HTMLResponse(content="<h1>多源舆情智能分析系统</h1>", status_code=200)
