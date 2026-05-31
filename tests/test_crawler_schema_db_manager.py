"""
测试 schema/db_manager.py — 数据库管理工具
"""

from pathlib import Path

project_root = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider" / "schema"))
import sys; from unittest.mock import MagicMock as _MM; sys.modules["models_bigdata"] = _MM()

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def db_manager():
    """创建 schema DatabaseManager 实例（mock connect）"""
    from schema.db_manager import DatabaseManager
    with patch.object(DatabaseManager, "connect"):
        mgr = DatabaseManager()
        mgr.engine = MagicMock()
        return mgr


class TestConnect:
    """connect 方法"""

    @patch("schema.db_manager.settings")
    def test_mysql_url(self, mock_s):
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        with patch("schema.db_manager.create_engine") as mock_ce:
            from schema.db_manager import DatabaseManager
            mgr = DatabaseManager.__new__(DatabaseManager)
            mgr.engine = MagicMock()
            mgr.connect()

        url = mock_ce.call_args[0][0]
        assert url.startswith("mysql+pymysql://")
        assert "utf8mb4" in url

    @patch("schema.db_manager.settings")
    def test_postgresql_url(self, mock_s):
        mock_s.DB_DIALECT = "postgresql"
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 5432
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8"

        with patch("schema.db_manager.create_engine") as mock_ce:
            from schema.db_manager import DatabaseManager
            mgr = DatabaseManager.__new__(DatabaseManager)
            mgr.engine = MagicMock()
            mgr.connect()

        url = mock_ce.call_args[0][0]
        assert url.startswith("postgresql+psycopg://")

    @patch("schema.db_manager.settings")
    def test_connect_exits_on_failure(self, mock_s):
        """连接失败时退出"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8"

        with patch("schema.db_manager.create_engine", side_effect=Exception("conn failed")):
            with pytest.raises(SystemExit):
                from schema.db_manager import DatabaseManager
                mgr = DatabaseManager.__new__(DatabaseManager)
                mgr.engine = MagicMock()
                mgr.connect()


class TestShowTables:
    """show_tables 方法"""

    def test_with_tables(self, db_manager):
        """有表时正常显示"""
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = [
            "daily_news", "daily_topics", "xhs_note", "douyin_aweme"
        ]

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_conn.execute.return_value = mock_result
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        with patch("schema.db_manager.inspect", return_value=mock_inspector):
            db_manager.show_tables()  # 只验证不抛异常

    def test_no_tables(self, db_manager):
        """无表时正常显示"""
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = []

        with patch("schema.db_manager.inspect", return_value=mock_inspector):
            db_manager.show_tables()

    def test_platform_table_query_fails_gracefully(self, db_manager):
        """平台表查询失败时显示查询失败"""
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["daily_news", "xhs_note"]

        mock_conn = MagicMock()

        def execute_side_effect(*args):
            if "xhs" in str(args[0]):
                raise Exception("table missing")
            result = MagicMock()
            result.scalar_one.return_value = 5
            return result

        mock_conn.execute.side_effect = execute_side_effect
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        with patch("schema.db_manager.inspect", return_value=mock_inspector):
            db_manager.show_tables()


class TestShowStatistics:
    """show_statistics 方法"""

    def test_normal(self, db_manager):
        """正常显示统计"""
        mock_conn = MagicMock()

        def execute_side_effect(*args):
            result = MagicMock()
            if "GROUP BY task_status" in str(args[0]):
                result.all.return_value = [("completed", 5)]
                result.scalar_one.return_value = 5
            elif "COUNT(DISTINCT crawl_date)" in str(args[0]):
                result.scalar_one.return_value = 3
            elif "COUNT(DISTINCT source_platform)" in str(args[0]):
                result.scalar_one.return_value = 2
            else:
                result.scalar_one.return_value = 10
            return result

        mock_conn.execute.side_effect = execute_side_effect
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        db_manager.show_statistics()

    def test_query_exception(self, db_manager):
        """查询失败时显示错误"""
        db_manager.engine.connect.side_effect = Exception("query failed")
        db_manager.show_statistics()


class TestShowRecentData:
    """show_recent_data 方法"""

    def test_has_data(self, db_manager):
        """有近期数据"""
        mock_conn = MagicMock()
        mock_result = MagicMock()

        def execute_side_effect(*args):
            r = MagicMock()
            if "daily_news" in str(args[0]):
                r.all.return_value = [("2026-05-06", 10, 2)]
            elif "daily_topics" in str(args[0]):
                r.all.return_value = [("2026-05-06", 3)]
            return r

        mock_conn.execute.side_effect = execute_side_effect
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        db_manager.show_recent_data(days=7)

    def test_no_data(self, db_manager):
        """无近期数据"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_conn.execute.return_value = mock_result
        db_manager.engine.connect.return_value.__enter__.return_value = mock_conn

        db_manager.show_recent_data(days=7)


class TestCleanupOldData:
    """cleanup_old_data 方法"""

    def test_dry_run(self, db_manager):
        """预览模式不执行删除"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_conn.execute.return_value = mock_result
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        db_manager.cleanup_old_data(days=90, dry_run=True)

        # 预览模式不应调用 DELETE
        for call in mock_conn.execute.call_args_list:
            assert "DELETE" not in str(call[0][0])

    def test_execute_deletes(self, db_manager):
        """执行模式删除数据"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_conn.execute.return_value = mock_result
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        db_manager.cleanup_old_data(days=90, dry_run=False)

        # 执行模式应该调用 DELETE
        delete_calls = [c for c in mock_conn.execute.call_args_list
                        if "DELETE" in str(c[0][0])]
        assert len(delete_calls) > 0

    def test_no_data_to_clean(self, db_manager):
        """无数据可清理"""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_conn.execute.return_value = mock_result
        db_manager.engine.begin.return_value.__enter__.return_value = mock_conn

        db_manager.cleanup_old_data(days=90, dry_run=False)
        # 应返回但无 DELETE 调用


class TestClose:
    """close 方法"""

    def test_close(self, db_manager):
        db_manager.close()
        db_manager.engine.dispose.assert_called_once()

    def test_close_no_engine(self):
        from schema.db_manager import DatabaseManager
        with patch.object(DatabaseManager, "connect"):
            mgr = DatabaseManager()
            mgr.engine = None
            mgr.close()  # 不应抛异常
