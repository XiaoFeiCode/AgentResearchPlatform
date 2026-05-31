"""System status routes."""

from fastapi import APIRouter
from pydantic import BaseModel


# App status router (kept at /api/status for frontend compatibility)
app_status_router = APIRouter(tags=["apps"])


@app_status_router.get("/api/status")
def get_app_status():
    return {"forum": {"status": "stopped", "port": None}}

router = APIRouter(prefix="/api/system", tags=["system"])


class StatusResponse(BaseModel):
    success: bool


@router.get("/status", response_model=StatusResponse)
def get_system_status():
    return {"success": True}
