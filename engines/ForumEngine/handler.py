"""
Event-driven forum handler — replaces the file-polling LogMonitor.

Subscribes to summary_ready events from the three search engines,
buffers them, writes to forum.log, and periodically triggers HOST
speech via LLM.
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from app.services.event_bus import publish, subscribe, unsubscribe
from app.services.event_types import EventType
from engines.ForumEngine.llm_host import generate_host_speech



class ForumEventHandler:
    """Listens to summary_ready events and manages forum session."""

    def __init__(self, log_dir: str = "logs"):
        self.forum_log_file = Path(log_dir) / "forum.log"
        self.forum_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Session state
        self.is_active = False
        self.buffer: List[str] = []
        self.is_host_generating = False
        self._lock = threading.Lock()

    def start(self):
        """Register event subscriber."""
        subscribe(self.on_event)
        logger.info("ForumEngine: 事件订阅已注册，论坛会话将持续活跃")

    def stop(self):
        """Unregister event subscriber and end session."""
        unsubscribe(self.on_event)
        self._end_session()
        logger.info("ForumEngine: 事件订阅已取消")

    def on_event(self, event_type: str, data: Dict):
        """Dispatch events from the event bus."""
        if event_type == EventType.SUMMARY_READY:
            self._handle_summary(data)

    KNOWN_SOURCES = {'insight', 'media', 'query'}

    def _handle_summary(self, data: Dict):
        source = data.get("source", "").strip().lower()
        if source not in self.KNOWN_SOURCES:
            logger.warning(f"ForumEngine: 收到未知来源的 SUMMARY_READY，source={source!r}，已丢弃")
            return
        summary = data.get("summary", "").strip()
        if not summary:
            return

        should_trigger = False
        with self._lock:
            if not self.is_active:
                self._start_session()

            self._write_forum_log(summary, source.upper())

            timestamp = datetime.now().strftime('%H:%M:%S')
            log_line = f"[{timestamp}] [{source.upper()}] {summary}"
            self.buffer.append(log_line)

            publish(EventType.FORUM_MESSAGE, {
                "type": "agent",
                "sender": f"{source.title()} Engine",
                "content": summary,
                "source": source,
                "timestamp": datetime.now().strftime('%H:%M:%S'),
            })

            if len(self.buffer) >= 5 and not self.is_host_generating:
                should_trigger = True

        # 在锁外触发 HOST，避免 _trigger_host 内部再次获取 _lock 导致死锁
        if should_trigger:
            self._trigger_host()

    def _start_session(self):
        """Begin a new forum session."""
        self.is_active = True
        self.buffer.clear()
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._write_forum_log(f"=== ForumEngine 论坛开始 - {start_time} ===", "SYSTEM")
        logger.info("ForumEngine: 论坛会话开始")

    def _end_session(self):
        """End the current forum session."""
        if not self.is_active:
            return
        self.is_active = False
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._write_forum_log(f"=== ForumEngine 论坛结束 - {end_time} ===", "SYSTEM")
        logger.info("ForumEngine: 论坛会话结束")

    def _trigger_host(self):
        """Generate HOST speech via LLM and publish it."""
        with self._lock:
            if self.is_host_generating:
                return
            self.is_host_generating = True
            if len(self.buffer) < 5:
                self.is_host_generating = False
                return

        try:
            recent = self.buffer[-5:]
            logger.info("ForumEngine: 正在生成主持人发言...")
            speech = generate_host_speech(recent)
            if speech:
                self._write_forum_log(speech, "HOST")
                # 将主持人发言publish出去，
                publish(EventType.FORUM_MESSAGE, {
                    "type": "host",
                    "sender": "Forum Host",
                    "content": speech,
                    "timestamp": datetime.now().strftime('%H:%M:%S'),
                })
                with self._lock:
                    self.buffer = self.buffer[5:]
        except Exception as e:
            logger.exception(f"ForumEngine: 主持人发言生成失败: {e}")
        finally:
            self.is_host_generating = False

    def _write_forum_log(self, content: str, source: Optional[str] = None):
        """Write a line to forum.log (thread-safe via GIL)."""
        try:
            with open(self.forum_log_file, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime('%H:%M:%S')
                line = content.replace('\n', '\\n').replace('\r', '\\r')
                tag = f" [{source}]" if source else ""
                f.write(f"[{ts}]{tag} {line}\n")
                f.flush()
        except Exception as e:
            logger.exception(f"ForumEngine: 写入forum.log失败: {e}")
