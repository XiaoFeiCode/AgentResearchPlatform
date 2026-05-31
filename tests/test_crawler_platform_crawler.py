"""
测试 DeepSentimentCrawling/platform_crawler.py — 平台爬虫管理器
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))

import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime


@pytest.fixture
def crawler():
    from DeepSentimentCrawling.platform_crawler import PlatformCrawler
    with patch("DeepSentimentCrawling.platform_crawler.Path.exists", return_value=True):
        with patch("DeepSentimentCrawling.platform_crawler.config"):
            c = PlatformCrawler()
            c.mediacrawler_path = MagicMock()
            return c


class TestInit:
    """__init__ 方法"""

    def test_media_crawler_not_found(self):
        """MediaCrawler 目录不存在时抛出 FileNotFoundError"""
        with patch("DeepSentimentCrawling.platform_crawler.Path.exists", return_value=False):
            with patch("DeepSentimentCrawling.platform_crawler.config"):
                from DeepSentimentCrawling.platform_crawler import PlatformCrawler
                with pytest.raises(FileNotFoundError):
                    PlatformCrawler()

    def test_supported_platforms(self, crawler):
        assert len(crawler.supported_platforms) == 7
        assert "xhs" in crawler.supported_platforms

    def test_crawl_stats_init(self, crawler):
        assert crawler.crawl_stats == {}


class TestConfigureDB:
    """configure_mediacrawler_db 方法"""

    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_configure_mysql(self, mock_config, crawler):
        mock_config.settings.DB_DIALECT = "mysql"
        mock_config.settings.DB_PASSWORD = "pwd"
        mock_config.settings.DB_USER = "user"
        mock_config.settings.DB_HOST = "host"
        mock_config.settings.DB_PORT = 3306
        mock_config.settings.DB_NAME = "db"

        fake_path = MagicMock()
        crawler.mediacrawler_path.__truediv__.return_value = fake_path
        fake_path.__truediv__.return_value = fake_path

        m = mock_open(read_data="old config")
        with patch("builtins.open", m):
            result = crawler.configure_mediacrawler_db()

        assert result is True

    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_configure_failure_returns_false(self, mock_config, crawler):
        crawler.mediacrawler_path.__truediv__.side_effect = Exception("file error")

        result = crawler.configure_mediacrawler_db()
        assert result is False


class TestCreateBaseConfig:
    """create_base_config 方法"""

    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_creates_config_for_platform(self, mock_config, crawler):
        mock_config.settings.DB_DIALECT = "mysql"

        m = mock_open(read_data="PLATFORM = \"old\"\nKEYWORDS = \"\"\nCRAWLER_TYPE = \"\"\nSAVE_DATA_OPTION = \"csv\"\nCRAWLER_MAX_NOTES_COUNT = 0\nENABLE_GET_COMMENTS = False\nCRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 0\nHEADLESS = False\n")
        with patch("builtins.open", m):
            result = crawler.create_base_config("xhs", ["AI", "大模型"], "search", 50)

        assert result is True

    def test_failure_returns_false(self, crawler):
        crawler.mediacrawler_path.__truediv__.side_effect = Exception("error")
        result = crawler.create_base_config("xhs", ["AI"])
        assert result is False


class TestRunCrawler:
    """run_crawler 方法"""

    @patch("DeepSentimentCrawling.platform_crawler.subprocess.run")
    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_run_success(self, mock_config, mock_run, crawler):
        mock_config.settings.DB_DIALECT = "mysql"
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(crawler, "configure_mediacrawler_db", return_value=True):
            with patch.object(crawler, "create_base_config", return_value=True):
                result = crawler.run_crawler("xhs", ["AI", "大模型"])

        assert result["success"] is True
        assert result["platform"] == "xhs"
        assert result["keywords_count"] == 2
        assert "duration_seconds" in result

    @patch("DeepSentimentCrawling.platform_crawler.subprocess.run")
    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_return_code_non_zero(self, mock_config, mock_run, crawler):
        mock_config.settings.DB_DIALECT = "mysql"
        mock_run.return_value = MagicMock(returncode=1)

        with patch.object(crawler, "configure_mediacrawler_db", return_value=True):
            with patch.object(crawler, "create_base_config", return_value=True):
                result = crawler.run_crawler("xhs", ["AI"])

        assert result["success"] is False
        assert result["return_code"] == 1

    def test_invalid_platform_raises(self, crawler):
        with pytest.raises(ValueError, match="不支持的平台"):
            crawler.run_crawler("invalid", ["AI"])

    def test_empty_keywords_raises(self, crawler):
        with pytest.raises(ValueError, match="不能为空"):
            crawler.run_crawler("xhs", [])

    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_db_config_fails(self, mock_config, crawler):
        with patch.object(crawler, "configure_mediacrawler_db", return_value=False):
            result = crawler.run_crawler("xhs", ["AI"])
        assert result["success"] is False

    @patch("DeepSentimentCrawling.platform_crawler.subprocess.run")
    @patch("DeepSentimentCrawling.platform_crawler.config")
    def test_timeout(self, mock_config, mock_run, crawler):
        import subprocess
        mock_config.settings.DB_DIALECT = "mysql"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3600)

        with patch.object(crawler, "configure_mediacrawler_db", return_value=True):
            with patch.object(crawler, "create_base_config", return_value=True):
                result = crawler.run_crawler("xhs", ["AI"])

        assert result["success"] is False
        assert "超时" in result.get("error", "")


class TestParseOutput:
    """_parse_crawl_output 方法"""

    def test_notes_and_comments(self):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()

        stats = c._parse_crawl_output(
            ["获取到 15 条笔记", "获取到 5 条评论"],
            []
        )
        assert stats["notes_count"] == 15
        assert stats["comments_count"] == 5

    def test_login_required(self):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()

        stats = c._parse_crawl_output(["需要登录才能继续"], [])
        assert stats["login_required"] is True

    def test_error_counting(self):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()

        stats = c._parse_crawl_output([], ["error: timeout", "发生异常"])
        assert stats["errors_count"] == 2


class TestMultiPlatformCrawl:
    """run_multi_platform_crawl_by_keywords 方法"""

    @patch.object(Path, "exists", return_value=True)
    def test_all_successful(self, mock_exists):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()
            c.supported_platforms = ['xhs', 'dy']
            c.crawl_stats = {}
            c.mediacrawler_path = MagicMock()

        c.run_crawler = MagicMock(return_value={"success": True, "notes_count": 10, "comments_count": 5})

        result = c.run_multi_platform_crawl_by_keywords(["AI", "大模型"], ["xhs", "dy"])
        assert result["successful_tasks"] == 4  # 2 kw * 2 platforms
        assert result["total_notes"] == 20
        assert result["failed_tasks"] == 0

    @patch.object(Path, "exists", return_value=True)
    def test_mixed_results(self, mock_exists):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()
            c.supported_platforms = ['xhs', 'dy']
            c.crawl_stats = {}
            c.mediacrawler_path = MagicMock()

        call_count = [0]
        def mock_run_crawler(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"success": True, "notes_count": 10}
            return {"success": False, "error": "failed"}
        c.run_crawler = mock_run_crawler

        result = c.run_multi_platform_crawl_by_keywords(["AI"], ["xhs", "dy"])
        assert result["successful_tasks"] == 1
        assert result["failed_tasks"] == 1


class TestCrawlStats:
    """get_crawl_statistics / save_crawl_log 方法"""

    def test_get_statistics(self):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()
            c.crawl_stats = {"xhs": {"success": True}}

        stats = c.get_crawl_statistics()
        assert stats["total_platforms"] == 1
        assert "xhs" in stats["platforms_crawled"]

    def test_save_crawl_log(self):
        from DeepSentimentCrawling.platform_crawler import PlatformCrawler
        with patch.object(PlatformCrawler, "__init__", return_value=None):
            c = PlatformCrawler()
            c.crawl_stats = {"xhs": {"success": True}}

        with patch("builtins.open", mock_open()):
            c.save_crawl_log("/tmp/test_log.json")
