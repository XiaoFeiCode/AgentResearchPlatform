"""Configuration read/write routes."""

from fastapi import APIRouter, HTTPException, Request

from app.services.system_service import read_config_values, write_config_values, CONFIG_KEYS

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config():
    try:
        values = read_config_values()
        return {"success": True, "config": values}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("")
async def update_config(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="请求体不能为空")

    updates = {}
    for key, value in payload.items():
        if key in CONFIG_KEYS:
            updates[key] = value if value is not None else ''

    if not updates:
        raise HTTPException(status_code=400, detail="没有可更新的配置项")

    try:
        write_config_values(updates)
        updated = read_config_values()
        return {"success": True, "config": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
