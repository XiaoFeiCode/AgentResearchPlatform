"""
Forum日志读取工具
通过 EventBus 订阅实时缓存 HOST 发言，避免每次读取文件。
"""

import threading
from typing import Optional

from app.services.event_bus import subscribe, unsubscribe
from app.services.event_types import EventType

# ── EventBus-backed cache ──────────────────────────────────────────

_latest_host_speech: Optional[str] = None
_cache_lock = threading.Lock()


def _on_forum_message(event_type: str, data: dict):
    """EventBus subscriber: cache latest HOST speech in memory."""
    global _latest_host_speech
    if event_type == EventType.FORUM_MESSAGE and data.get("type") == "host":
        content = data.get("content", "")
        if content:
            with _cache_lock:
                _latest_host_speech = content


def init_forum_reader():
    """Register HOST speech cache subscriber."""
    subscribe(_on_forum_message)


def shutdown_forum_reader():
    """Unregister HOST speech cache subscriber."""
    global _latest_host_speech
    unsubscribe(_on_forum_message)
    with _cache_lock:
        _latest_host_speech = None


# ── Public API ─────────────────────────────────────────────────────

def get_latest_host_speech(log_dir: str = "logs") -> Optional[str]:
    """
    获取最新的HOST发言（从 EventBus 内存缓存读取）。

    Args:
        log_dir: 日志目录路径（保留参数兼容性，当前不再使用）

    Returns:
        最新的HOST发言内容，如果没有则返回None
    """
    with _cache_lock:
        return _latest_host_speech


def format_host_speech_for_prompt(host_speech: str) -> str:
    """
    格式化HOST发言，用于添加到prompt中

    Args:
        host_speech: HOST发言内容

    Returns:
        格式化后的内容
    """
    if not host_speech:
        return ""

    return f"""
### 论坛主持人最新总结
以下是论坛主持人对各Agent讨论的最新总结和引导，请参考其中的观点和建议：

{host_speech}

---
"""
