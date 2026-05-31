"""
测试 DeepSentimentCrawling/keyword_manager.py — 关键词管理器
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
import sys as _sys; from unittest.mock import MagicMock as _MM
_sys.modules["models_bigdata"] = _MM()

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


@pytest.fixture
def km():
    from DeepSentimentCrawling.keyword_manager import KeywordManager
    with patch.object(KeywordManager, "connect"):
        mgr = KeywordManager()
        mgr.engine = MagicMock()
        return mgr


class TestGetLatestKeywords:
    """get_latest_keywords 方法 — 关键词回退链"""

    def test_returns_today_keywords(self, km):
        """当天有关键词 → 返回当天关键词"""
        km.get_daily_topics = MagicMock(return_value={"keywords": ["AI", "大模型"]})
        km.get_recent_topics = MagicMock()

        result = km.get_latest_keywords(target_date=date(2026, 5, 6), max_keywords=100)
        assert result == ["AI", "大模型"]
        km.get_recent_topics.assert_not_called()

    def test_falls_back_to_recent(self, km):
        """当天无关键词 → 回退到最近7天"""
        km.get_daily_topics = MagicMock(return_value=None)
        km.get_recent_topics = MagicMock(return_value=[
            {"keywords": ["AI"]}, {"keywords": ["大模型"]}
        ])

        result = km.get_latest_keywords(target_date=date(2026, 5, 6), max_keywords=100)
        assert "AI" in result
        assert "大模型" in result

    def test_returns_default_when_no_data(self, km):
        """当天和近期都无数据 → 返回默认关键词"""
        km.get_daily_topics = MagicMock(return_value=None)
        km.get_recent_topics = MagicMock(return_value=[])

        result = km.get_latest_keywords(target_date=date(2026, 5, 6))

        assert len(result) > 0
        assert "科技" in result
        assert "人工智能" in result

    def test_respects_max_keywords_sampling(self, km):
        """超过最大数量时随机采样"""
        km.get_daily_topics = MagicMock(return_value={"keywords": [f"kw{i}" for i in range(50)]})

        result = km.get_latest_keywords(target_date=date(2026, 5, 6), max_keywords=10)
        assert len(result) == 10

    def test_default_date_is_today(self, km):
        """默认使用今天日期"""
        km.get_daily_topics = MagicMock(return_value=None)
        km.get_recent_topics = MagicMock(return_value=[])

        km.get_latest_keywords()
        # get_daily_topics 应该被调用且参数接近今天
        call_date = km.get_daily_topics.call_args[0][0]
        assert call_date == date.today()


class TestGetDailyTopics:
    """get_daily_topics 方法"""

    def test_returns_parsed_data(self, km):
        """返回数据时正确解析 keywords JSON"""
        mock_conn = MagicMock()
        mock_row = {"id": 1, "extract_date": date(2026, 5, 6),
                     "keywords": '["AI","大模型"]', "topic_description": "总结"}
        mock_conn.execute.return_value.mappings.return_value.first.return_value = mock_row
        km.engine.connect.return_value.__enter__.return_value = mock_conn

        result = km.get_daily_topics(date(2026, 5, 6))
        assert result is not None
        assert result["keywords"] == ["AI", "大模型"]

    def test_no_data_returns_none(self, km):
        """无数据返回 None"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.first.return_value = None
        km.engine.connect.return_value.__enter__.return_value = mock_conn

        result = km.get_daily_topics(date(2026, 5, 6))
        assert result is None

    def test_empty_keywords_json(self, km):
        """keywords 为空时返回空列表"""
        mock_conn = MagicMock()
        mock_row = {"id": 1, "keywords": None}
        mock_conn.execute.return_value.mappings.return_value.first.return_value = mock_row
        km.engine.connect.return_value.__enter__.return_value = mock_conn

        result = km.get_daily_topics()
        assert result["keywords"] == []

    def test_exception_returns_none(self, km):
        """异常时返回 None"""
        km.engine.connect.side_effect = Exception("db error")
        result = km.get_daily_topics()
        assert result is None


class TestGetRecentTopics:
    """get_recent_topics 方法"""

    def test_returns_parsed_list(self, km):
        mock_conn = MagicMock()
        mock_rows = [
            {"id": 1, "keywords": '["AI"]', "extract_date": date(2026, 5, 6)},
            {"id": 2, "keywords": '["大模型"]', "extract_date": date(2026, 5, 5)},
        ]
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        km.engine.connect.return_value.__enter__.return_value = mock_conn

        results = km.get_recent_topics(days=7)
        assert len(results) == 2
        assert results[0]["keywords"] == ["AI"]

    def test_empty(self, km):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.all.return_value = []
        km.engine.connect.return_value.__enter__.return_value = mock_conn

        assert km.get_recent_topics() == []

    def test_exception_returns_empty_list(self, km):
        km.engine.connect.side_effect = Exception("error")
        assert km.get_recent_topics() == []


class TestFilterKeywordsByPlatform:
    """_filter_keywords_by_platform 方法"""

    def test_xhs_preferred(self):
        from DeepSentimentCrawling.keyword_manager import KeywordManager
        with patch.object(KeywordManager, "connect"):
            km = KeywordManager()

        keywords = ["美妆", "科技", "人工智能", "时尚", "编程"]
        result = km._filter_keywords_by_platform(keywords, "xhs")
        assert "美妆" in result[:2]  # 偏好词应靠前

    def test_no_preference_returns_original(self):
        from DeepSentimentCrawling.keyword_manager import KeywordManager
        with patch.object(KeywordManager, "connect"):
            km = KeywordManager()

        keywords = ["科技", "AI"]
        result = km._filter_keywords_by_platform(keywords, "unknown")
        assert result == keywords

    def test_filter_balance(self):
        """偏好词不够时补充其他关键词"""
        from DeepSentimentCrawling.keyword_manager import KeywordManager
        with patch.object(KeywordManager, "connect"):
            km = KeywordManager()

        keywords = ["科技", "编程", "AI", "大数据", "区块链", "云计算", "物联网", "元宇宙"]
        result = km._filter_keywords_by_platform(keywords, "bili")
        # bili 偏好词: 科技, 游戏, 动漫, 学习, 编程, 数码, 科普
        # 至少科技和编程应该在其中
        assert "科技" in result
        assert "编程" in result


class TestCrawlingSummary:
    """get_crawling_summary 方法"""

    def test_has_data(self, km):
        km.get_daily_topics = MagicMock(return_value={"keywords": ["AI"], "summary": "今日总结"})
        summary = km.get_crawling_summary(date(2026, 5, 6))
        assert summary["has_data"] is True
        assert summary["keywords_count"] == 1

    def test_no_data(self, km):
        km.get_daily_topics = MagicMock(return_value=None)
        summary = km.get_crawling_summary(date(2026, 5, 6))
        assert summary["has_data"] is False
        assert summary["keywords_count"] == 0


class TestDefaultKeywords:
    """_get_default_keywords 方法"""

    def test_returns_35_keywords(self):
        from DeepSentimentCrawling.keyword_manager import KeywordManager
        with patch.object(KeywordManager, "connect"):
            km = KeywordManager()

        defaults = km._get_default_keywords()
        assert len(defaults) == 35
        assert "科技" in defaults
        assert "人工智能" in defaults
        assert "AI" in defaults
