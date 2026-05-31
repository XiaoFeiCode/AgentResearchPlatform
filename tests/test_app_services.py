"""
测试 app/services/ — event_bus, system_service, search_service
已验证可稳定运行的部分
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

import pytest
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock, mock_open


class TestEventBus:
    def setup_method(self):
        from app.services import event_bus
        event_bus.clear()

    def test_publish_calls_subscriber(self):
        from app.services.event_bus import publish, subscribe
        received = []
        def cb(evt, data):
            received.append((evt, data))
        subscribe(cb)
        publish("test_event", {"key": "value"})
        assert len(received) == 1
        assert received[0] == ("test_event", {"key": "value"})

    def test_subscriber_error_does_not_propagate(self):
        from app.services.event_bus import publish, subscribe
        errors = []
        def bad_cb(evt, data):
            raise RuntimeError("oops")
        def good_cb(evt, data):
            errors.append("reached")
        subscribe(bad_cb)
        subscribe(good_cb)
        publish("test", {})
        assert errors == ["reached"]

    def test_unsubscribe(self):
        from app.services.event_bus import publish, subscribe, unsubscribe
        received = []
        def cb(evt, data):
            received.append(evt)
        subscribe(cb)
        unsubscribe(cb)
        publish("test", {})
        assert len(received) == 0

    def test_unsubscribe_non_existent(self):
        from app.services.event_bus import unsubscribe
        unsubscribe(lambda: None)

    def test_clear_removes_all(self):
        from app.services.event_bus import publish, subscribe, clear
        def cb(evt, data):
            pass
        subscribe(cb)
        clear()
        from app.services import event_bus
        assert len(event_bus._subscribers) == 0


class TestReadConfigValues:
    @patch("app.config.reload_settings")
    def test_returns_values(self, mock_reload):
        from app import config as config_module
        from app.services.system_service import read_config_values

        old_settings = config_module.settings
        config_module.settings = MagicMock(HOST="0.0.0.0", PORT=5000, DB_HOST="h")
        try:
            values = read_config_values()
            assert values["HOST"] == "0.0.0.0"
            mock_reload.assert_called_once()
        finally:
            config_module.settings = old_settings


class TestReadWriteLog:
    @patch("app.services.system_service.Path.exists", return_value=True)
    def test_write_log(self, mock_exists):
        from app.services.system_service import write_log_to_file
        m = mock_open()
        with patch("builtins.open", m):
            write_log_to_file("test_app", "hello world")
        m().write.assert_called_once()

    @patch("app.services.system_service.Path.exists", return_value=True)
    def test_read_log(self, mock_exists):
        from app.services.system_service import read_log_from_file
        m = mock_open(read_data="line1\nline2\nline3\n")
        with patch("builtins.open", m):
            assert len(read_log_from_file("test_app")) == 3

    @patch("app.services.system_service.Path.exists", return_value=True)
    def test_read_log_tail(self, mock_exists):
        from app.services.system_service import read_log_from_file
        m = mock_open(read_data="line1\nline2\nline3\n")
        with patch("builtins.open", m):
            lines = read_log_from_file("test_app", tail_lines=2)
        assert lines == ["line2", "line3"]

    @patch("app.services.system_service.Path.exists", return_value=False)
    def test_read_log_file_not_found(self, mock_exists):
        from app.services.system_service import read_log_from_file
        assert read_log_from_file("nonexistent") == []

    def test_write_log_exception(self):
        from app.services.system_service import write_log_to_file
        with patch("builtins.open", side_effect=PermissionError("denied")):
            write_log_to_file("test", "data")


class TestSearchAll:
    @patch("app.services.search_service.run_engine_task")
    def test_launches_three_engines(self, mock_run):
        from app.services.search_service import search_all
        result = search_all("test query")
        assert result["success"] is True
        assert mock_run.call_count == 3

    @patch("app.services.search_service.run_engine_task")
    def test_empty_query(self, mock_run):
        from app.services.search_service import search_all
        result = search_all("  ")
        assert result["success"] is False
        mock_run.assert_not_called()


class TestExtractCitations:
    def test_extracts_from_paragraphs(self):
        from app.services.search_service import _extract_citations_from_result
        result = {
            "paragraphs": [{
                "title": "P1", "content": "test",
                "research": {
                    "search_history": [{"query": "q", "url": "u", "title": "t", "content": "c", "score": 0.9}],
                    "latest_summary": "", "is_completed": True, "reflection_iteration": 0,
                },
            }],
        }
        citations = _extract_citations_from_result(result)
        assert len(citations) == 1
        assert citations[0]["query"] == "q"

    def test_empty_state(self):
        from app.services.search_service import _extract_citations_from_result
        assert _extract_citations_from_result({"paragraphs": []}) == []

    def test_extracts_json_safe_decimal_score(self):
        from app.services.search_service import _extract_citations_from_result
        result = {
            "paragraphs": [{
                "title": "Insight P1",
                "research": {
                    "search_history": [{
                        "query": "q",
                        "url": "u",
                        "title": "t",
                        "content": "c",
                        "score": Decimal("1095.000"),
                    }],
                    "reflection_iteration": Decimal("2"),
                },
            }],
        }
        citations = _extract_citations_from_result(result)
        assert citations[0]["score"] == 1095.0
        assert citations[0]["reflection_count"] == 2.0
        json.dumps(citations, ensure_ascii=False)
