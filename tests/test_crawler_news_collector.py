"""
测试SentinelSpider - BroadTopicExtraction新闻收集器

测试NewsCollector的API调用、数据处理和错误处理能力
"""

from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

project_root = Path(__file__).parent.parent

import pytest
import json
import httpx


# ==================== 模拟数据 ====================

MOCK_WEIBO_RESPONSE = {
    "status": "success",
    "id": "weibo",
    "updatedTime": 1778061317553,
    "items": [
        {"id": "item1", "title": "测试热搜第一条", "url": "https://weibo.com/test1"},
        {"id": "item2", "title": "测试热搜第二条", "url": "https://weibo.com/test2"},
        {"id": "item3", "title": "测试热搜第三条", "url": "https://weibo.com/test3"},
    ]
}

MOCK_ZHIHU_RESPONSE = {
    "status": "success",
    "id": "zhihu",
    "updatedTime": 1778061317553,
    "items": [
        {"id": "2035011255342032293", "title": "测试问题一？", "url": "https://zhihu.com/question/1"},
        {"id": "2035011255342032294", "title": "测试问题二？", "url": "https://zhihu.com/question/2"},
    ]
}

MOCK_BILI_RESPONSE = {
    "status": "success",
    "id": "bilibili-hot-search",
    "updatedTime": 1778061317553,
    "items": [
        {"id": "bw1", "title": "测试B站视频一", "url": "https://bilibili.com/video/bw1"},
        {"id": "bw2", "title": "测试B站视频二", "url": "https://bilibili.com/video/bw2"},
    ]
}

API_BASE_URL = "https://newsnow.busiyi.world"


class TestNewsCollectorFetch:
    """测试NewsCollector.fetch_news方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        # 先添加路径再导入
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector, SOURCE_NAMES
        self.NewsCollector = NewsCollector
        self.SOURCE_NAMES = SOURCE_NAMES
        # Mock database_manager to avoid DB connection
        self._db_patch = patch(
            "tools.SentinelSpider.BroadTopicExtraction.get_today_news.DatabaseManager"
        )
        self._db_patch.start()
        yield
        self._db_patch.stop()

    def _make_mock_client(self, status_code=200, json_data=None, exc=None):
        """创建模拟的httpx.AsyncClient"""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = AsyncMock(spec=httpx.Response)
        if exc:
            response.raise_for_status.side_effect = exc
        else:
            response.status_code = status_code
            if json_data:
                response.json.return_value = json_data
        client.get.return_value = response
        client.__aenter__.return_value = client
        # 确保get返回response
        return client

    @pytest.mark.asyncio
    async def test_fetch_news_success(self):
        """测试成功获取新闻"""
        mock_client = self._make_mock_client(json_data=MOCK_WEIBO_RESPONSE)
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "success"
        assert result["source"] == "weibo"
        assert len(result["data"]["items"]) == 3
        assert result["data"]["items"][0]["title"] == "测试热搜第一条"

    @pytest.mark.asyncio
    async def test_fetch_news_timeout(self):
        """测试请求超时处理"""
        mock_client = self._make_mock_client(exc=httpx.TimeoutException("timeout"))
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "timeout"
        assert "超时" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_news_http_error(self):
        """测试HTTP错误处理"""
        mock_client = self._make_mock_client(exc=httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404)
        ))
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "http_error"
        assert "HTTP错误" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_news_unknown_error(self):
        """测试未知错误处理"""
        mock_client = self._make_mock_client(exc=ValueError("something broke"))
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "error"
        assert "未知错误" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_news_json_empty_items(self):
        """测试返回空items的情况"""
        empty_resp = {"status": "success", "id": "weibo", "items": []}
        mock_client = self._make_mock_client(json_data=empty_resp)
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "success"
        assert len(result["data"]["items"]) == 0

    @pytest.mark.asyncio
    async def test_fetch_news_missing_items_field(self):
        """测试返回数据缺少items字段"""
        no_items_resp = {"status": "success", "id": "weibo"}
        mock_client = self._make_mock_client(json_data=no_items_resp)
        collector = self.NewsCollector()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await collector.fetch_news("weibo")

        assert result["status"] == "success"
        assert "items" not in result["data"]


class TestNewsCollectorProcess:
    """测试NewsCollector的数据处理方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector
        self.NewsCollector = NewsCollector
        self._db_patch = patch(
            "tools.SentinelSpider.BroadTopicExtraction.get_today_news.DatabaseManager"
        )
        self._db_patch.start()
        yield
        self._db_patch.stop()

    def test_process_news_item_dict(self):
        """测试处理字典类型的新闻项"""
        collector = self.NewsCollector()
        item = {"id": "abc123", "title": "测试新闻标题", "url": "https://example.com"}
        result = collector._process_news_item(item, "weibo", 1)

        assert result is not None
        assert result["id"] == "weibo_abc123"
        assert result["title"] == "测试新闻标题"
        assert result["url"] == "https://example.com"
        assert result["source"] == "weibo"
        assert result["rank"] == 1

    def test_process_news_item_string(self):
        """测试处理字符串类型的新闻项"""
        collector = self.NewsCollector()
        result = collector._process_news_item("原始字符串新闻", "zhihu", 2)

        assert result is not None
        assert result["title"] == "原始字符串新闻"
        assert result["source"] == "zhihu"
        assert result["rank"] == 2
        assert result["url"] == ""

    def test_process_news_item_long_title(self):
        """测试超长标题截断"""
        collector = self.NewsCollector()
        long_title = "x" * 200
        item = {"id": "long1", "title": long_title}
        result = collector._process_news_item(item, "test", 1)

        # 字符串类型会裁剪到100字符
        item2 = "y" * 200
        result2 = collector._process_news_item(item2, "test", 2)

        assert len(result2["title"]) == 100

    def test_process_news_item_missing_id(self):
        """测试缺少id字段的情况"""
        collector = self.NewsCollector()
        item = {"title": "只有标题"}
        result = collector._process_news_item(item, "weibo", 3)

        assert result is not None
        assert result["id"] == "weibo_rank_3"
        assert result["title"] == "只有标题"

    def test_process_news_results_success(self):
        """测试处理成功的结果列表"""
        collector = self.NewsCollector()
        results = [
            {"source": "weibo", "status": "success",
             "data": {"items": [{"id": "1", "title": "新闻1"}]}},
            {"source": "zhihu", "status": "success",
             "data": {"items": [{"id": "2", "title": "新闻2"}, {"id": "3", "title": "新闻3"}]}},
        ]

        processed = collector._process_news_results(results)

        assert processed["success"] is True
        assert processed["successful_sources"] == 2
        assert processed["total_sources"] == 2
        assert processed["total_news"] == 3
        assert len(processed["news_list"]) == 3

    def test_process_news_results_with_failures(self):
        """测试混合成功/失败结果的处理"""
        collector = self.NewsCollector()
        results = [
            {"source": "weibo", "status": "success",
             "data": {"items": [{"id": "1", "title": "新闻1"}]}},
            {"source": "zhihu", "status": "timeout",
             "error": "超时了", "timestamp": ""},
            {"source": "bili", "status": "http_error",
             "error": "500错误", "timestamp": ""},
        ]

        processed = collector._process_news_results(results)

        assert processed["success"] is True
        assert processed["successful_sources"] == 1
        assert processed["total_sources"] == 3
        assert processed["total_news"] == 1
        assert len(processed["news_list"]) == 1

    def test_process_news_results_all_fail(self):
        """测试全部失败的情况"""
        collector = self.NewsCollector()
        results = [
            {"source": "weibo", "status": "timeout", "error": "超时", "timestamp": ""},
            {"source": "zhihu", "status": "error", "error": "挂了", "timestamp": ""},
        ]

        processed = collector._process_news_results(results)

        assert processed["success"] is True
        assert processed["successful_sources"] == 0
        assert processed["total_news"] == 0
        assert len(processed["news_list"]) == 0


class TestNewsCollectorGetPopular:
    """测试NewsCollector.get_popular_news方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector
        self.NewsCollector = NewsCollector
        self._db_patch = patch(
            "tools.SentinelSpider.BroadTopicExtraction.get_today_news.DatabaseManager"
        )
        self._db_patch.start()
        yield
        self._db_patch.stop()

    @pytest.mark.asyncio
    async def test_get_popular_news_default_sources(self):
        """测试使用默认源列表获取新闻"""
        collector = self.NewsCollector()

        # Mock fetch_news 返回成功
        async def mock_fetch(source):
            return {
                "source": source,
                "status": "success",
                "data": {"items": [{"id": "1", "title": "新闻"}]},
                "timestamp": "2026-05-06T12:00:00"
            }
        collector.fetch_news = mock_fetch

        results = await collector.get_popular_news(sources=["weibo", "zhihu"])

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_get_popular_news_mixed(self):
        """测试混合成功/失败的多源获取"""
        collector = self.NewsCollector()

        call_count = 0

        async def mock_fetch(source):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"source": source, "status": "success",
                        "data": {"items": [{"id": "1", "title": "新闻"}]},
                        "timestamp": ""}
            else:
                return {"source": source, "status": "timeout",
                        "error": f"{source} 超时", "timestamp": ""}

        collector.fetch_news = mock_fetch
        results = await collector.get_popular_news(sources=["weibo", "zhihu"])

        assert results[0]["status"] == "success"
        assert results[1]["status"] == "timeout"


class TestNewsCollectorCollectAndSave:
    """测试NewsCollector.collect_and_save_news方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector, SOURCE_NAMES
        self.NewsCollector = NewsCollector
        self.SOURCE_NAMES = SOURCE_NAMES
        # Mock db_manager
        self._db_manager_patch = patch(
            "tools.SentinelSpider.BroadTopicExtraction.get_today_news.DatabaseManager"
        )
        mock_db = self._db_manager_patch.start()
        mock_db_instance = MagicMock()
        mock_db_instance.save_daily_news.return_value = 3
        mock_db.return_value = mock_db_instance
        self.mock_db_instance = mock_db_instance
        yield
        self._db_manager_patch.stop()

    @pytest.mark.asyncio
    async def test_collect_and_save_success(self):
        """测试完整的收集和保存流程"""
        collector = self.NewsCollector()

        # Mock get_popular_news
        async def mock_get_popular(sources=None):
            return [
                {"source": "weibo", "status": "success",
                 "data": {"items": [{"id": "1", "title": "新闻1"},
                                    {"id": "2", "title": "新闻2"}]},
                 "timestamp": ""}
            ]
        collector.get_popular_news = mock_get_popular

        result = await collector.collect_and_save_news(sources=["weibo"])

        assert result["success"] is True
        assert result["total_news"] == 2
        assert result["successful_sources"] == 1
        assert result["saved_count"] == 3  # mock_db.save_daily_news return value
        self.mock_db_instance.save_daily_news.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_and_save_no_news(self):
        """测试没有获取到新闻的情况"""
        collector = self.NewsCollector()

        async def mock_get_popular(sources=None):
            return [{"source": "weibo", "status": "error",
                     "error": "失败", "timestamp": ""}]

        collector.get_popular_news = mock_get_popular
        result = await collector.collect_and_save_news(sources=["weibo"])

        # 即使没有新闻也应该返回success=False
        assert "news_list" in result
        assert result["total_news"] == 0

    @pytest.mark.asyncio
    async def test_collect_and_save_db_failure(self):
        """测试数据库保存失败的情况"""
        collector = self.NewsCollector()
        self.mock_db_instance.save_daily_news.return_value = 0

        async def mock_get_popular(sources=None):
            return [{"source": "weibo", "status": "success",
                     "data": {"items": [{"id": "1", "title": "新闻1"}]},
                     "timestamp": ""}]

        collector.get_popular_news = mock_get_popular
        result = await collector.collect_and_save_news(sources=["weibo"])

        # 采集成功但DB保存返回0
        assert result["success"] is True
        assert result["saved_count"] == 0
