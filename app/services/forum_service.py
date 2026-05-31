"""
Forum service — in-memory forum message store and start/stop control.

Core flow uses EventBus; forum.log is a plain log file (not part of data flow).
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.event_bus import subscribe, unsubscribe
from engines.ForumEngine.handler import ForumEventHandler

LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

_forum_handler: Optional[ForumEventHandler] = None

# In-memory message store (replaces file-based polling)
MAX_FORUM_MESSAGES = 2000
_forum_messages: List[Dict[str, Any]] = []


_KNOWN_SENDERS = {'Insight Engine', 'Media Engine', 'Query Engine', 'Forum Host'}

def _on_forum_message(event_type: str, data: Dict[str, Any]):
    """Listen to FORUM_MESSAGE events and accumulate in memory."""
    sender = data.get('sender', '')
    if sender not in _KNOWN_SENDERS:
        return
    timestamp = datetime.now().strftime('%H:%M:%S')
    msg = {
        'type': data.get('type', 'agent'),
        'sender': sender,
        'content': data.get('content', ''),
        'timestamp': timestamp,
        'source': data.get('source', ''),
    }
    _forum_messages.append(msg)
    if len(_forum_messages) > MAX_FORUM_MESSAGES:
        _forum_messages[:] = _forum_messages[-MAX_FORUM_MESSAGES:]


def init_forum_log():
    """Initialize forum.log with a header line and subscribe to FORUM_MESSAGE events."""
    forum_log_file = LOG_DIR / "forum.log"
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(forum_log_file, 'w', encoding='utf-8') as f:
        f.write(f"=== ForumEngine 系统初始化 - {start_time} ===\n")
    subscribe(_on_forum_message)
    logger.info("ForumEngine: forum.log 已初始化，EventBus 消息订阅已注册")


def shutdown_forum_service():
    """Stop ForumEngine and unregister EventBus subscriptions."""
    stop_forum_engine()
    unsubscribe(_on_forum_message)


def start_forum_engine():
    """Start the ForumEventHandler."""
    global _forum_handler
    try:
        if _forum_handler is not None:
            return True

        _forum_handler = ForumEventHandler()
        _forum_handler.start()
        logger.info("ForumEngine: 论坛事件处理器已启动")
        return True
    except Exception as e:
        logger.exception(f"ForumEngine: 启动论坛失败: {e}")
        return False


def stop_forum_engine():
    global _forum_handler
    try:
        if _forum_handler is not None:
            _forum_handler.stop()
            _forum_handler = None
            logger.info("ForumEngine: 论坛已停止")
    except Exception as e:
        logger.exception(f"ForumEngine: 停止论坛失败: {e}")


def get_forum_log() -> Dict[str, Any]:
    """Return accumulated messages from in-memory store."""
    return {
        'log_lines': [],  # deprecated, kept for API compatibility
        'parsed_messages': list(_forum_messages),
        'total_lines': len(_forum_messages),
    }


def parse_forum_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a forum.log line (utility for log analysis, not core flow)."""
    pattern = r'\[(\d{2}:\d{2}:\d{2})\]\s*\[([^\]]+)\]\s*(.*)'
    match = re.match(pattern, line)
    if not match:
        return None

    timestamp, raw_source, content = match.groups()
    source = raw_source.strip().upper()

    if source == 'SYSTEM' or not content.strip():
        return None
    if source not in ['QUERY', 'INSIGHT', 'MEDIA', 'HOST']:
        return None

    cleaned_content = content.replace('\\n', '\n').replace('\\r', '').strip()

    if source == 'HOST':
        message_type = 'host'
        sender = 'Forum Host'
    else:
        message_type = 'agent'
        sender = f'{source.title()} Engine'

    return {
        'type': message_type,
        'sender': sender,
        'content': cleaned_content,
        'timestamp': timestamp,
        'source': source,
    }
