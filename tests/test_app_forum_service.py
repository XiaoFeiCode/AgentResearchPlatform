"""
测试 app/services/forum_service.py — 论坛服务

forum.log is a plain log file; core data flow uses EventBus + in-memory store.
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch


class TestParseForumLogLine:
    """parse_forum_log_line remains as a log-analysis utility (not core flow)."""

    def test_parses_host_message(self):
        from app.services.forum_service import parse_forum_log_line
        r = parse_forum_log_line("[10:00:01] [HOST] 发言")
        assert r["type"] == "host"
        assert r["sender"] == "Forum Host"
        assert r["content"] == "发言"

    def test_parses_agent_message(self):
        from app.services.forum_service import parse_forum_log_line
        r = parse_forum_log_line("[10:00:02] [INSIGHT] 洞察")
        assert r["type"] == "agent"
        assert r["sender"] == "Insight Engine"
        assert r["source"] == "INSIGHT"

    def test_rejects_system(self):
        from app.services.forum_service import parse_forum_log_line
        assert parse_forum_log_line("[10:00:00] [SYSTEM] init") is None

    def test_rejects_empty(self):
        from app.services.forum_service import parse_forum_log_line
        assert parse_forum_log_line("[10:00:00] [HOST]  ") is None

    def test_rejects_invalid_source(self):
        from app.services.forum_service import parse_forum_log_line
        assert parse_forum_log_line("[10:00:00] [UNKNOWN] text") is None

    def test_no_match(self):
        from app.services.forum_service import parse_forum_log_line
        assert parse_forum_log_line("bad format") is None

    def test_escaped_newlines(self):
        from app.services.forum_service import parse_forum_log_line
        r = parse_forum_log_line("[10:00:00] [HOST] a\\nb")
        assert "\n" in r["content"]

    def test_media_agent(self):
        from app.services.forum_service import parse_forum_log_line
        r = parse_forum_log_line("[10:00:00] [MEDIA] media result")
        assert r["sender"] == "Media Engine"

    def test_query_agent(self):
        from app.services.forum_service import parse_forum_log_line
        r = parse_forum_log_line("[10:00:00] [QUERY] query result")
        assert r["sender"] == "Query Engine"


class TestGetForumLog:
    """get_forum_log reads from in-memory store (not file)."""

    def test_returns_messages_from_memory(self):
        """Populate _forum_messages and verify get_forum_log returns them."""
        from app.services import forum_service as fs

        # Save original state
        original = list(fs._forum_messages)
        fs._forum_messages.clear()
        try:
            fs._forum_messages.append({
                'type': 'agent', 'sender': 'Insight Engine',
                'content': 'test', 'timestamp': '10:00:00', 'source': 'INSIGHT',
            })
            fs._forum_messages.append({
                'type': 'host', 'sender': 'Forum Host',
                'content': 'hello', 'timestamp': '10:00:01', 'source': 'HOST',
            })

            r = fs.get_forum_log()
            assert r["total_lines"] == 2
            assert len(r["parsed_messages"]) == 2
            assert r["parsed_messages"][0]["source"] == "INSIGHT"
            assert r["parsed_messages"][1]["source"] == "HOST"
        finally:
            fs._forum_messages[:] = original

    def test_returns_empty_when_no_messages(self):
        from app.services import forum_service as fs

        original = list(fs._forum_messages)
        fs._forum_messages.clear()
        try:
            r = fs.get_forum_log()
            assert r["total_lines"] == 0
            assert r["parsed_messages"] == []
        finally:
            fs._forum_messages[:] = original
