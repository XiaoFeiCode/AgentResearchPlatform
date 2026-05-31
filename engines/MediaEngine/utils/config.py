"""
MediaEngine 配置 — 复用全局 settings，不再维护独立副本。
"""
from app.config import Settings, settings  # noqa: F401
