"""
测试 DeepSentimentCrawling/main.py — 深度情感爬取编排
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider" / "DeepSentimentCrawling"))

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


@pytest.fixture
def crawler():
    from DeepSentimentCrawling.main import DeepSentimentCrawling
    with patch("DeepSentimentCrawling.main.KeywordManager"):
        with patch("DeepSentimentCrawling.main.PlatformCrawler"):
            c = DeepSentimentCrawling()
            c.keyword_manager = MagicMock()
            c.platform_crawler = MagicMock()
            return c


class TestInit:
    def test_supported_platforms(self, crawler):
        assert crawler.supported_platforms == ['xhs', 'dy', 'ks', 'bili', 'wb', 'tieba', 'zhihu']

    def test_creates_components(self):
        with patch("DeepSentimentCrawling.main.KeywordManager") as mock_km:
            with patch("DeepSentimentCrawling.main.PlatformCrawler") as mock_pc:
                from DeepSentimentCrawling.main import DeepSentimentCrawling
                dsc = DeepSentimentCrawling()
                mock_km.assert_called_once()
                mock_pc.assert_called_once()


class TestRunDailyCrawling:
    """run_daily_crawling 方法"""

    def test_success(self, crawler):
        crawler.keyword_manager.get_crawling_summary.return_value = {
            "has_data": True, "keywords_count": 2, "date": date(2026, 5, 6)
        }
        crawler.keyword_manager.get_latest_keywords.return_value = ["AI", "大模型"]
        crawler.platform_crawler.run_multi_platform_crawl_by_keywords.return_value = {
            "successful_tasks": 3, "total_tasks": 4,
            "total_keywords": 2, "total_platforms": 2, "total_notes": 10
        }

        result = crawler.run_daily_crawling(
            target_date=date(2026, 5, 6),
            platforms=["xhs", "wb"],
            max_keywords_per_platform=50,
            max_notes_per_platform=50
        )

        assert result["success"] is True
        assert result["crawl_results"]["successful_tasks"] == 3

    def test_no_topic_data(self, crawler):
        crawler.keyword_manager.get_crawling_summary.return_value = {
            "has_data": False
        }

        result = crawler.run_daily_crawling()
        assert result["success"] is False
        assert "没有话题数据" in result.get("error", "")

    def test_no_keywords(self, crawler):
        crawler.keyword_manager.get_crawling_summary.return_value = {
            "has_data": True, "keywords_count": 0
        }
        crawler.keyword_manager.get_latest_keywords.return_value = []

        result = crawler.run_daily_crawling()
        assert result["success"] is False
        assert "没有关键词" in result.get("error", "")

    def test_default_date_and_platforms(self, crawler):
        crawler.keyword_manager.get_crawling_summary.return_value = {
            "has_data": True, "keywords_count": 2
        }
        crawler.keyword_manager.get_latest_keywords.return_value = ["AI"]
        crawler.platform_crawler.run_multi_platform_crawl_by_keywords.return_value = {"successful_tasks": 1, "total_tasks": 7, "total_keywords": 1, "total_platforms": 7, "total_notes": 5}

        # 不传参数时使用默认值
        crawler.run_daily_crawling()
        assert crawler.keyword_manager.get_crawling_summary.call_args[0][0] == date.today()


class TestRunPlatformCrawling:
    """run_platform_crawling 方法"""

    def test_success(self, crawler):
        crawler.keyword_manager.get_keywords_for_platform.return_value = ["AI"]
        crawler.platform_crawler.run_crawler.return_value = {"success": True}

        result = crawler.run_platform_crawling("xhs",
            target_date=date(2026, 5, 6), max_keywords=50, max_notes=50)
        assert result["success"] is True

    def test_invalid_platform(self, crawler):
        with pytest.raises(ValueError, match="不支持的平台"):
            crawler.run_platform_crawling("invalid")

    def test_no_keywords(self, crawler):
        crawler.keyword_manager.get_keywords_for_platform.return_value = []
        result = crawler.run_platform_crawling("xhs")
        assert result["success"] is False


class TestListTopics:
    """list_available_topics 方法"""

    def test_has_topics(self, crawler):
        crawler.keyword_manager.db_manager.get_recent_topics.return_value = [
            {"extract_date": date(2026, 5, 6), "keywords": ["AI"], "summary": "今日总结"},
            {"extract_date": date(2026, 5, 5), "keywords": ["大模型"], "summary": "昨日"},
        ]
        crawler.list_available_topics(days=7)

    def test_no_topics(self, crawler):
        crawler.keyword_manager.db_manager.get_recent_topics.return_value = []
        crawler.list_available_topics(days=7)


class TestClose:
    """close 方法"""

    def test_close(self, crawler):
        crawler.close()
        crawler.keyword_manager.close.assert_called_once()
