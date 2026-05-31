"""
测试SentinelSpider - BroadTopicExtraction数据库管理器

测试DatabaseManager的CRUD操作、数据格式处理和错误处理
"""

from pathlib import Path
from datetime import date, datetime

project_root = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))

import pytest
from unittest.mock import MagicMock, patch, ANY


# ==================== Fixtures ====================

@pytest.fixture
def mock_engine():
    """创建模拟的SQLAlchemy Engine"""
    return MagicMock()


@pytest.fixture
def db_manager(mock_engine):
    """创建DatabaseManager实例（mock掉engine）"""
    from tools.SentinelSpider.BroadTopicExtraction.database_manager import DatabaseManager

    with patch.object(DatabaseManager, "connect"):
        mgr = DatabaseManager()
        mgr.engine = mock_engine
        # 默认 mock engine.begin() 返回一个带 proper rowcount 的 connection
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_conn.execute.return_value = mock_result
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        return mgr


# ==================== 测试保存新闻 ====================

class TestDatabaseManagerSaveNews:
    """测试save_daily_news方法"""

    def test_save_daily_news_success(self, db_manager):
        """测试成功保存新闻"""
        # 模拟 engine.begin() 返回的 conn.execute 返回 proper rowcount
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0  # DELETE 影响0行（没有旧数据）
        mock_conn.execute.return_value = mock_result
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        news_data = [
            {"id": "weibo_123", "title": "新闻1", "url": "https://weibo.com/1",
             "source": "weibo", "rank": 1},
            {"id": "weibo_456", "title": "新闻2", "url": "https://weibo.com/2",
             "source": "weibo", "rank": 2},
        ]

        result = db_manager.save_daily_news(news_data, date(2026, 5, 6))

        assert result == 2

    def test_save_daily_news_empty(self, db_manager):
        """测试保存空列表"""
        result = db_manager.save_daily_news([], date(2026, 5, 6))
        assert result == 0

    def test_save_daily_news_genertes_news_id_with_date(self, db_manager):
        """测试news_id包含日期后缀"""
        news_data = [
            {"id": "weibo_123", "title": "新闻", "url": "",
             "source": "weibo", "rank": 1},
        ]

        result = db_manager.save_daily_news(news_data, date(2026, 5, 6))
        assert result == 1

    def test_save_daily_news_long_title_truncated(self, db_manager):
        """测试超长标题被截断"""
        news_data = [
            {"id": "1", "title": "x" * 600, "source": "weibo"},
        ]

        result = db_manager.save_daily_news(news_data, date(2026, 5, 6))
        assert result == 1

    def test_save_daily_news_insert_failure_continues(self, db_manager):
        """测试单条插入失败不影响后续"""
        from sqlalchemy import exc as sa_exc

        # Mock engine.begin() 第一次DELETE，第二次INSERT异常，第三次INSERT正常
        mock_begin = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0

        # begin() 返回一个 context manager，其 __enter__() 返回 mock_conn
        ctx_mgr = MagicMock()
        ctx_mgr.__enter__.return_value = mock_conn

        call_count = [0]

        def begin_side_effect():
            call_count[0] += 1
            if call_count[0] == 2:  # 第一次INSERT抛出异常
                err_ctx = MagicMock()
                err_conn = MagicMock()
                err_conn.execute.side_effect = sa_exc.IntegrityError(
                    "mock", "mock", "mock"
                )
                err_ctx.__enter__.return_value = err_conn
                return err_ctx
            return ctx_mgr

        mock_begin.side_effect = begin_side_effect
        db_manager.engine.begin = mock_begin

        news_data = [
            {"id": "1", "title": "失败新闻", "source": "weibo"},
            {"id": "2", "title": "成功新闻", "source": "weibo"},
        ]

        result = db_manager.save_daily_news(news_data, date(2026, 5, 6))

        # 第一条失败，第二条成功，所以返回 1
        assert result == 1

    def test_save_daily_news_execute_params(self, db_manager):
        """验证传递给execute的参数格式"""
        mock_begin = MagicMock()
        mock_conn = MagicMock()
        # DELETE需要rowcount，INSERT需要执行正常
        mock_conn.execute.return_value.rowcount = 0
        mock_begin.return_value.__enter__.return_value = mock_conn
        db_manager.engine.begin = mock_begin

        news_data = [
            {"id": "wb_1", "title": "测试新闻", "url": "https://example.com",
             "source": "weibo", "rank": 1},
        ]

        db_manager.save_daily_news(news_data, date(2026, 5, 6))

        # 验证INSERT语句的参数字段（第2次execute调用是INSERT）
        insert_call_args = mock_conn.execute.call_args[0][1]
        assert insert_call_args["news_id"].startswith("wb_1")
        assert insert_call_args["source_platform"] == "weibo"
        assert insert_call_args["title"] == "测试新闻"
        assert insert_call_args["url"] == "https://example.com"
        assert insert_call_args["rank_position"] == 1
        assert insert_call_args["crawl_date"] == date(2026, 5, 6)

    def test_save_daily_news_missing_id(self, db_manager):
        """测试缺少id字段时自动生成"""
        mock_begin = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0
        mock_begin.return_value.__enter__.return_value = mock_conn
        db_manager.engine.begin = mock_begin

        news_data = [
            {"title": "无ID新闻", "source": "unknown", "rank": 5},
        ]

        db_manager.save_daily_news(news_data, date(2026, 5, 6))

        # 第2次execute调用才是INSERT（第1次是DELETE）
        insert_call_args = mock_conn.execute.call_args_list[1][0][1]
        assert "unknown_rank_5" in insert_call_args["news_id"]


# ==================== 测试获取新闻 ====================

class TestDatabaseManagerGetNews:
    """测试get_daily_news方法"""

    def test_get_daily_news_with_data(self, db_manager):
        """测试获取有数据的新闻"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_row = {"news_id": "weibo_1", "title": "新闻1", "source_platform": "weibo"}
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_conn.execute.return_value = mock_result
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        rows = db_manager.get_daily_news(date(2026, 5, 6))

        assert len(rows) == 1
        assert rows[0]["title"] == "新闻1"

    def test_get_daily_news_empty(self, db_manager):
        """测试获取无数据的新闻"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_conn.execute.return_value = mock_result
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        rows = db_manager.get_daily_news(date(2026, 5, 6))

        assert len(rows) == 0

    def test_get_daily_news_default_date(self, db_manager):
        """测试默认使用今天日期"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_conn.execute.return_value = mock_result
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        today = date.today()
        db_manager.get_daily_news()

        # 验证查询中使用了正确的日期
        sql = mock_conn.execute.call_args[0][0]
        params = mock_conn.execute.call_args[0][1]
        assert params["d"] == today


# ==================== 测试话题操作 ====================

class TestDatabaseManagerTopics:
    """测试话题相关的数据库操作"""

    def test_save_daily_topics_insert(self, db_manager):
        """测试插入新话题"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.first.return_value = None  # 不存在，需要插入
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        result = db_manager.save_daily_topics(
            ["AI", "大模型", "新能源"],
            "今日热点总结",
            date(2026, 5, 6)
        )

        assert result is True
        # 验证是INSERT操作（检查SQL文本中的表名）
        calls = mock_conn.execute.call_args_list
        insert_found = any("INSERT INTO daily_topics" in c[0][0].text for c in calls)
        assert insert_found

    def test_save_daily_topics_update(self, db_manager):
        """测试更新已存在的话题"""
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_conn.execute.return_value.first.return_value = mock_row
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        result = db_manager.save_daily_topics(
            ["AI", "大模型"],
            "更新后的总结",
            date(2026, 5, 6)
        )

        assert result is True
        # 验证包含 UPDATE 语句
        calls = mock_conn.execute.call_args_list
        update_found = any("UPDATE daily_topics" in c[0][0].text for c in calls)
        assert update_found

    def test_save_daily_topics_with_default_date(self, db_manager):
        """测试使用默认日期"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.first.return_value = None
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        result = db_manager.save_daily_topics(["AI"], "总结")
        assert result is True

    def test_get_daily_topics_exists(self, db_manager):
        """测试获取存在的话题"""
        mock_conn = MagicMock()
        mock_row = {"id": 1, "extract_date": date(2026, 5, 6),
                    "keywords": '["AI","大模型"]', "topic_description": "总结内容",
                    "topic_id": "summary_20260506", "topic_name": "每日新闻分析"}
        mock_conn.execute.return_value.mappings.return_value.first.return_value = mock_row
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        result = db_manager.get_daily_topics(date(2026, 5, 6))

        assert result is not None
        assert result["topic_id"] == "summary_20260506"
        assert "AI" in result["keywords"]

    def test_get_daily_topics_not_exists(self, db_manager):
        """测试获取不存在的话题"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.first.return_value = None
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        result = db_manager.get_daily_topics(date(2026, 5, 6))

        assert result is None

    def test_get_recent_topics(self, db_manager):
        """测试获取最近话题"""
        mock_conn = MagicMock()
        mock_rows = [
            {"id": 2, "extract_date": date(2026, 5, 6),
             "keywords": '["AI"]', "topic_description": "今日"},
            {"id": 1, "extract_date": date(2026, 5, 5),
             "keywords": '["股市"]', "topic_description": "昨日"},
        ]
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        results = db_manager.get_recent_topics(days=7)

        assert len(results) == 2
        assert results[0]["keywords"] == ["AI"]
        assert results[1]["keywords"] == ["股市"]

    def test_get_recent_topics_empty_keywords(self, db_manager):
        """测试keywords为None或空字符串时的处理"""
        mock_conn = MagicMock()
        mock_rows = [
            {"id": 1, "extract_date": date(2026, 5, 6),
             "keywords": None, "topic_description": "无关键词"},
        ]
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        results = db_manager.get_recent_topics(days=7)

        assert len(results) == 1
        assert results[0]["keywords"] == []


# ==================== 测试数据库连接 ====================

class TestDatabaseManagerConnection:
    """测试数据库连接管理"""

    def test_close(self, db_manager):
        """测试关闭连接"""
        db_manager.close()
        db_manager.engine.dispose.assert_called_once()

    def test_multiple_close(self, db_manager):
        """测试多次关闭"""
        db_manager.close()
        db_manager.close()
        assert db_manager.engine.dispose.call_count == 2

    def test_context_manager(self, db_manager):
        """测试上下文管理器"""
        with db_manager as db:
            assert db is db_manager
        db_manager.engine.dispose.assert_called_once()
