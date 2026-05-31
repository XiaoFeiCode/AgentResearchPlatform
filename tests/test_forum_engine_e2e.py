"""
端到端测试：ForumEngine

ForumEngine uses ForumEventHandler (event-driven) instead of the old
file-polling LogMonitor.  forum.log is a plain log file; core data flow
uses EventBus + in-memory store.
"""

import sys
from pathlib import Path

import pytest

_proj_root = Path(__file__).resolve().parent.parent
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))

# 预注册 retry_helper
import types as _types
_rh = _types.ModuleType("retry_helper")
_rh.with_graceful_retry = lambda config=None, default_return=None: (lambda f: f)
_rh.SEARCH_API_RETRY_CONFIG = None
sys.modules["retry_helper"] = _rh


class TestParseForumLogLine:
    """parse_forum_log_line — 纯函数，日志分析工具（非核心流程）。"""

    def test_parse_agent_line(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:15] [INSIGHT] 这是洞察引擎的分析结果"
        result = parse_forum_log_line(line)
        assert result is not None
        assert result["type"] == "agent"
        assert result["sender"] == "Insight Engine"
        assert result["content"] == "这是洞察引擎的分析结果"
        assert result["source"] == "INSIGHT"
        assert result["timestamp"] == "10:30:15"

    def test_parse_host_line(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:20] [HOST] 各位好，欢迎来到本次讨论。"
        result = parse_forum_log_line(line)
        assert result is not None
        assert result["type"] == "host"
        assert result["sender"] == "Forum Host"
        assert result["source"] == "HOST"

    def test_parse_system_line_returns_none(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:00] [SYSTEM] === ForumEngine 监控开始 ==="
        assert parse_forum_log_line(line) is None

    def test_parse_empty_content_returns_none(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:00] [INSIGHT]  "
        assert parse_forum_log_line(line) is None

    def test_parse_malformed_line_returns_none(self):
        from app.services.forum_service import parse_forum_log_line
        assert parse_forum_log_line("普通文本，没有格式") is None
        assert parse_forum_log_line("") is None
        assert parse_forum_log_line("[BROKEN] no timestamp") is None

    def test_parse_unknown_source_returns_none(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:00] [UNKNOWN] 未知来源"
        assert parse_forum_log_line(line) is None

    def test_parse_line_with_escaped_newlines(self):
        from app.services.forum_service import parse_forum_log_line
        line = "[10:30:00] [MEDIA] 第一行\\n第二行\\n第三行"
        result = parse_forum_log_line(line)
        assert result is not None
        assert result["content"] == "第一行\n第二行\n第三行"

    def test_parse_all_three_agent_sources(self):
        from app.services.forum_service import parse_forum_log_line
        for source in ["QUERY", "MEDIA", "INSIGHT"]:
            line = f"[10:30:00] [{source}] 内容"
            result = parse_forum_log_line(line)
            assert result is not None, f"{source} 未被识别"
            assert result["source"] == source


class TestGetForumLog:
    """get_forum_log 从内存读取（不再从文件读取）。"""

    def test_get_forum_log_returns_messages_from_memory(self):
        from app.services import forum_service as fs

        original = list(fs._forum_messages)
        fs._forum_messages.clear()
        try:
            fs._forum_messages.append({
                'type': 'agent', 'sender': 'Insight Engine',
                'content': '洞察引擎分析', 'timestamp': '10:00:00', 'source': 'INSIGHT',
            })
            fs._forum_messages.append({
                'type': 'host', 'sender': 'Forum Host',
                'content': '主持人发言', 'timestamp': '10:00:01', 'source': 'HOST',
            })

            result = fs.get_forum_log()
            assert result["total_lines"] == 2
            assert len(result["parsed_messages"]) == 2
            assert result["parsed_messages"][0]["source"] == "INSIGHT"
            assert result["parsed_messages"][1]["source"] == "HOST"
        finally:
            fs._forum_messages[:] = original

    def test_get_forum_log_returns_empty_when_no_messages(self):
        from app.services import forum_service as fs

        original = list(fs._forum_messages)
        fs._forum_messages.clear()
        try:
            result = fs.get_forum_log()
            assert result["total_lines"] == 0
            assert result["parsed_messages"] == []
        finally:
            fs._forum_messages[:] = original
