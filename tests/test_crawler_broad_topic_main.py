"""
测试 BroadTopicExtraction/main.py — 话题提取编排层

覆盖 BroadTopicExtraction 类、run_extraction_command 和 CLI 入口
"""

from pathlib import Path

project_root = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date


# ==================== Fixtures ====================

@pytest.fixture
def mock_news_collector():
    return MagicMock()

@pytest.fixture
def mock_topic_extractor():
    return MagicMock()

@pytest.fixture
def mock_db_manager():
    return MagicMock()

@pytest.fixture
def extractor(mock_news_collector, mock_topic_extractor, mock_db_manager):
    """创建 BroadTopicExtraction 实例（所有子模块 mock）"""
    # 先设置 OpenAI API key 环境变量，避免 TopicExtractor 崩溃
    import os
    old_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test-key"

    from tools.SentinelSpider.BroadTopicExtraction.main import BroadTopicExtraction

    with patch.object(BroadTopicExtraction, "close", return_value=None):
        ext = BroadTopicExtraction()
        ext.news_collector = mock_news_collector
        ext.topic_extractor = mock_topic_extractor
        ext.db_manager = mock_db_manager

    if old_key:
        os.environ["OPENAI_API_KEY"] = old_key
    else:
        del os.environ["OPENAI_API_KEY"]
    return ext


SAMPLE_NEWS_RESULT = {
    "success": True,
    "news_list": [{"id": "wb_1", "title": "新闻1", "source": "weibo"}],
    "total_news": 1,
    "successful_sources": 1,
    "total_sources": 1,
}


# ==================== 初始化 ====================

class TestInit:
    """测试初始化"""

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.NewsCollector")
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.TopicExtractor")
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.DatabaseManager")
    def test_init_creates_components(self, mock_db, mock_te, mock_nc):
        """初始化时创建三个子模块"""
        from tools.SentinelSpider.BroadTopicExtraction.main import BroadTopicExtraction

        with patch.object(BroadTopicExtraction, "close"):
            ext = BroadTopicExtraction()

        mock_nc.assert_called_once()
        mock_te.assert_called_once()
        mock_db.assert_called_once()

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.NewsCollector")
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.TopicExtractor")
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.DatabaseManager")
    def test_context_manager(self, mock_db, mock_te, mock_nc):
        """上下文管理器正常关闭"""
        from tools.SentinelSpider.BroadTopicExtraction.main import BroadTopicExtraction

        with patch.object(BroadTopicExtraction, "close") as mock_close:
            with BroadTopicExtraction() as ext:
                pass

        mock_close.assert_called_once()

    def test_close_calls_submodules(self, extractor):
        """close 调用子模块的 close"""
        extractor.close()
        extractor.news_collector.close.assert_called_once()
        extractor.db_manager.close.assert_called_once()


# ==================== 每日话题提取 ====================

class TestRunDailyExtraction:
    """run_daily_extraction 方法"""

    @pytest.mark.asyncio
    async def test_full_success(self, extractor, mock_news_collector,
                                 mock_topic_extractor, mock_db_manager):
        """三步全部成功 → success=True"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value=SAMPLE_NEWS_RESULT)
        mock_topic_extractor.extract_keywords_and_summary.return_value = (["AI", "大模型"], "今日总结")
        mock_db_manager.save_daily_topics.return_value = True

        result = await extractor.run_daily_extraction(news_sources=["weibo"], max_keywords=50)

        assert result["success"] is True
        assert result["news_collection"]["success"] is True
        assert result["topic_extraction"]["keywords_count"] == 2
        assert result["database_save"]["success"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_news_collection_fails(self, extractor, mock_news_collector):
        """新闻采集失败 → 流程中止"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value={
            "success": False, "news_list": [], "total_news": 0,
            "successful_sources": 0, "total_sources": 1
        })

        result = await extractor.run_daily_extraction()

        assert result["success"] is False
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_news_collection_empty_list(self, extractor, mock_news_collector):
        """新闻列表为空 → 流程中止"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value={
            "success": True, "news_list": [], "total_news": 0,
            "successful_sources": 0, "total_sources": 1
        })

        result = await extractor.run_daily_extraction()

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_topic_extraction_empty_keywords(self, extractor, mock_news_collector,
                                                    mock_topic_extractor, mock_db_manager):
        """关键词为空 → 继续但记录警告"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value=SAMPLE_NEWS_RESULT)
        mock_topic_extractor.extract_keywords_and_summary.return_value = ([], "总结内容")

        result = await extractor.run_daily_extraction()

        assert result["topic_extraction"]["keywords_count"] == 0

    @pytest.mark.asyncio
    async def test_db_save_fails_but_flow_continues(self, extractor, mock_news_collector,
                                                     mock_topic_extractor, mock_db_manager):
        """DB 保存失败 → success=True（错误只记录在 database_save 中）"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value=SAMPLE_NEWS_RESULT)
        mock_topic_extractor.extract_keywords_and_summary.return_value = (["AI"], "总结")
        mock_db_manager.save_daily_topics.return_value = False

        result = await extractor.run_daily_extraction()

        assert result["success"] is True
        assert result["database_save"]["success"] is False

    @pytest.mark.asyncio
    async def test_result_contains_all_keys(self, extractor, mock_news_collector,
                                             mock_topic_extractor, mock_db_manager):
        """返回结果包含所有期望的字段"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value=SAMPLE_NEWS_RESULT)
        mock_topic_extractor.extract_keywords_and_summary.return_value = (["AI"], "总结")
        mock_db_manager.save_daily_topics.return_value = True

        result = await extractor.run_daily_extraction()

        assert "extraction_date" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "news_collection" in result
        assert "topic_extraction" in result
        assert "database_save" in result

    @pytest.mark.asyncio
    async def test_default_args(self, extractor, mock_news_collector,
                                 mock_topic_extractor, mock_db_manager):
        """测试默认参数"""
        mock_news_collector.collect_and_save_news = AsyncMock(return_value=SAMPLE_NEWS_RESULT)
        mock_topic_extractor.extract_keywords_and_summary.return_value = (["AI"], "总结")
        mock_db_manager.save_daily_topics.return_value = True

        result = await extractor.run_daily_extraction()

        # 不传参数时默认使用全部源和 100 个关键词
        assert result["success"] is True


# ==================== 获取关键词 ====================

class TestGetKeywords:
    """get_keywords_for_crawling 方法"""

    def test_has_data(self, extractor, mock_db_manager, mock_topic_extractor):
        """数据库有数据 → 返回搜索关键词"""
        mock_db_manager.get_daily_topics.return_value = {
            "keywords": ["AI", "大模型", "新能源汽车"]
        }
        mock_topic_extractor.get_search_keywords.return_value = ["AI", "大模型"]

        result = extractor.get_keywords_for_crawling(extract_date=date(2026, 5, 6))

        assert result == ["AI", "大模型"]
        mock_db_manager.get_daily_topics.assert_called_with(date(2026, 5, 6))

    def test_no_data(self, extractor, mock_db_manager):
        """数据库无数据 → 返回空列表"""
        mock_db_manager.get_daily_topics.return_value = None

        result = extractor.get_keywords_for_crawling()

        assert result == []

    def test_default_date(self, extractor, mock_db_manager):
        """默认使用今天日期"""
        mock_db_manager.get_daily_topics.return_value = None

        extractor.get_keywords_for_crawling()
        mock_db_manager.get_daily_topics.assert_called_once()

    def test_empty_keywords_list(self, extractor, mock_db_manager, mock_topic_extractor):
        """关键词为空列表的情况"""
        mock_db_manager.get_daily_topics.return_value = {"keywords": []}
        mock_topic_extractor.get_search_keywords.return_value = []

        result = extractor.get_keywords_for_crawling()

        assert result == []


# ==================== 获取分析结果 ====================

class TestGetAnalysis:
    """get_daily_analysis / get_recent_analysis 方法"""

    def test_daily_analysis_has_data(self, extractor, mock_db_manager):
        """get_daily_analysis 有数据"""
        mock_db_manager.get_daily_topics.return_value = {
            "keywords": ["AI"], "topic_description": "测试"
        }

        result = extractor.get_daily_analysis(target_date=date(2026, 5, 6))

        assert result is not None
        assert result["keywords"] == ["AI"]

    def test_daily_analysis_no_data(self, extractor, mock_db_manager):
        """get_daily_analysis 无数据"""
        mock_db_manager.get_daily_topics.return_value = None

        result = extractor.get_daily_analysis()

        assert result is None

    def test_recent_analysis(self, extractor, mock_db_manager):
        """get_recent_analysis"""
        mock_db_manager.get_recent_topics.return_value = [
            {"keywords": ["AI"], "topic_description": "今日"}
        ]

        result = extractor.get_recent_analysis(days=7)

        assert len(result) == 1
        mock_db_manager.get_recent_topics.assert_called_with(7)

    def test_recent_analysis_empty(self, extractor, mock_db_manager):
        """get_recent_analysis 无数据"""
        mock_db_manager.get_recent_topics.return_value = []

        result = extractor.get_recent_analysis()

        assert result == []


# ==================== 打印结果 ====================

class TestPrintResults:
    """print_extraction_results 方法"""

    def test_print_with_keywords(self, extractor):
        """有关键词时打印"""
        result = {
            "news_collection": {"total_news": 10, "successful_sources": 2, "total_sources": 3},
            "topic_extraction": {"keywords_count": 5, "keywords": ["AI", "大模型", "新能源", "股市", "教育"],
                                 "summary": "今日热点总结内容"},
            "database_save": {"success": True},
        }

        # 只验证不抛异常
        extractor.print_extraction_results(result)

    def test_print_without_keywords(self, extractor):
        """无关键词时打印"""
        result = {
            "news_collection": {"total_news": 0, "successful_sources": 0, "total_sources": 0},
            "topic_extraction": {"keywords_count": 0, "keywords": [], "summary": ""},
            "database_save": {"success": False},
        }

        extractor.print_extraction_results(result)


# ==================== 异步 CLI ====================

class TestRunExtractionCommand:
    """run_extraction_command 异步 CLI 函数"""

    class _MockExtractor:
        """模拟 BroadTopicExtraction，sync/async 方法控制精确"""
        def __init__(self):
            self.run_daily_extraction = AsyncMock(return_value={
                "success": True,
                "news_collection": {"total_news": 5},
                "topic_extraction": {"keywords_count": 3, "keywords": ["AI"]},
                "database_save": {"success": True},
            })
            self.get_keywords_for_crawling = MagicMock(return_value=["AI", "大模型"])
            self.get_daily_analysis = MagicMock(return_value={})
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass

    @pytest.mark.asyncio
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.BroadTopicExtraction")
    @patch("builtins.open")
    async def test_success(self, mock_open, mock_extractor_cls):
        """成功执行"""
        mock_extractor_cls.return_value = self._MockExtractor()

        from tools.SentinelSpider.BroadTopicExtraction.main import run_extraction_command
        result = await run_extraction_command(sources=["weibo"], keywords_count=50, show_details=False)
        assert result is True

    @pytest.mark.asyncio
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.BroadTopicExtraction")
    async def test_failure(self, mock_extractor_cls):
        """执行失败"""
        ext = self._MockExtractor()
        ext.run_daily_extraction = AsyncMock(return_value={"success": False, "error": "采集失败"})
        mock_extractor_cls.return_value = ext

        from tools.SentinelSpider.BroadTopicExtraction.main import run_extraction_command
        result = await run_extraction_command(show_details=False)
        assert result is False

    @pytest.mark.asyncio
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.BroadTopicExtraction")
    async def test_exception(self, mock_extractor_cls):
        """内部抛异常时返回 False"""
        class _CrashExtractor:
            async def __aenter__(self):
                raise Exception("unexpected error")
            async def __aexit__(self, *a):
                pass
        mock_extractor_cls.return_value = _CrashExtractor()

        from tools.SentinelSpider.BroadTopicExtraction.main import run_extraction_command
        result = await run_extraction_command()
        assert result is False

    @pytest.mark.asyncio
    @patch("tools.SentinelSpider.BroadTopicExtraction.main.BroadTopicExtraction")
    async def test_empty_keywords_not_saved(self, mock_extractor_cls):
        """关键词为空时跳过文件保存"""
        ext = self._MockExtractor()
        ext.run_daily_extraction = AsyncMock(return_value={
            "success": True,
            "news_collection": {"total_news": 5},
            "topic_extraction": {"keywords_count": 0, "keywords": []},
            "database_save": {"success": True},
        })
        ext.get_keywords_for_crawling = MagicMock(return_value=[])
        mock_extractor_cls.return_value = ext

        from tools.SentinelSpider.BroadTopicExtraction.main import run_extraction_command
        result = await run_extraction_command(show_details=False)
        assert result is True


# ==================== CLI 入口 ====================

class TestCLI:
    """main() CLI 入口"""

    def test_list_sources(self):
        """--list-sources 列出新闻源"""
        with patch("sys.argv", ["main.py", "--list-sources"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            main()  # --list-sources returns without exit

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.run_extraction_command")
    def test_default_run(self, mock_run):
        """无参数时运行提取"""
        mock_run.return_value = True
        with patch("sys.argv", ["main.py"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            with pytest.raises(SystemExit):
                main()

        mock_run.assert_called_once()

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.run_extraction_command")
    def test_with_sources(self, mock_run):
        """--sources 参数"""
        mock_run.return_value = True
        with patch("sys.argv", ["main.py", "--sources", "weibo", "zhihu"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            with pytest.raises(SystemExit):
                main()

        _, kwargs = mock_run.call_args
        assert kwargs.get("sources") == ["weibo", "zhihu"]

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.run_extraction_command")
    def test_keywords_count(self, mock_run):
        """--keywords 参数"""
        mock_run.return_value = True
        with patch("sys.argv", ["main.py", "--keywords", "50"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            with pytest.raises(SystemExit):
                main()

        _, kwargs = mock_run.call_args
        assert kwargs.get("keywords_count") == 50

    @patch("tools.SentinelSpider.BroadTopicExtraction.main.run_extraction_command")
    def test_quiet_mode(self, mock_run):
        """--quiet 参数"""
        mock_run.return_value = True
        with patch("sys.argv", ["main.py", "--quiet"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            with pytest.raises(SystemExit):
                main()

        _, kwargs = mock_run.call_args
        assert kwargs.get("show_details") is False

    def test_invalid_keywords_exits(self):
        """关键词超出范围时退出"""
        with patch("sys.argv", ["main.py", "--keywords", "300"]):
            from tools.SentinelSpider.BroadTopicExtraction.main import main
            with pytest.raises(SystemExit):
                main()
