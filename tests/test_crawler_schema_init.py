"""
测试 schema/init_database.py — 数据库初始化脚本
"""

from pathlib import Path

project_root = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider" / "schema"))
import sys; from unittest.mock import MagicMock as _MM; sys.modules["models_bigdata"] = _MM()

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# Mock models_bigdata to avoid duplicate SQLAlchemy table definitions
import sys
sys.modules["models_bigdata"] = MagicMock()
sys.modules["schema.models_bigdata"] = MagicMock()


class TestEnv:
    """_env 辅助函数"""

    def test_env_exists(self):
        from schema.init_database import _env
        import os
        os.environ["TEST_VAR_1"] = "value"
        assert _env("TEST_VAR_1") == "value"
        del os.environ["TEST_VAR_1"]

    def test_env_missing(self):
        from schema.init_database import _env
        assert _env("NONEXISTENT_VAR") is None

    def test_env_empty_string(self):
        from schema.init_database import _env
        import os
        os.environ["TEST_EMPTY"] = ""
        assert _env("TEST_EMPTY") is None
        del os.environ["TEST_EMPTY"]

    def test_env_default(self):
        from schema.init_database import _env
        assert _env("NONEXISTENT", "default") == "default"


class TestBuildDatabaseURL:
    """_build_database_url 函数"""

    @patch("schema.init_database.settings")
    def test_mysql_default(self, mock_s):
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "myhost"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "user"
        mock_s.DB_PASSWORD = "pass"
        mock_s.DB_NAME = "mydb"

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert url.startswith("mysql+aiomysql://user:pass@myhost:3306/mydb")

    @patch("schema.init_database.settings")
    def test_mysql_defaults_fallback(self, mock_s):
        """当配置为空时使用默认值"""
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = ""
        mock_s.DB_HOST = ""
        mock_s.DB_PORT = None
        mock_s.DB_USER = ""
        mock_s.DB_PASSWORD = ""
        mock_s.DB_NAME = ""

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert "localhost" in url
        assert "root" in url

    @patch("schema.init_database.settings")
    def test_postgresql(self, mock_s):
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = "postgresql"
        mock_s.DB_HOST = "pghost"
        mock_s.DB_PORT = 5432
        mock_s.DB_USER = "pguser"
        mock_s.DB_PASSWORD = "pgpass"
        mock_s.DB_NAME = "pgdb"

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert url.startswith("postgresql+asyncpg://pguser:pgpass@pghost:5432/pgdb")

    @patch("schema.init_database.settings")
    def test_password_special_chars(self, mock_s):
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p@ss"
        mock_s.DB_NAME = "d"

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert "p%40ss" in url  # @ → %40

    @patch("schema.init_database.settings")
    def test_database_url_preferred(self, mock_s):
        """DATABASE_URL 优先"""
        mock_s.DATABASE_URL = "postgresql+asyncpg://custom"
        mock_s.DB_DIALECT = "mysql"

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert url == "postgresql+asyncpg://custom"

    @patch("schema.init_database.settings")
    def test_port_defaults_by_dialect(self, mock_s):
        """端口根据 dialect 选择默认值"""
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = "postgresql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = None
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"

        from schema.init_database import _build_database_url
        url = _build_database_url()
        assert ":5432" in url


class TestCreateViews:
    """_create_views_if_needed 函数"""

    def _make_engine_mock(self):
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_conn = AsyncMock()
        mock_begin_ctx.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value = mock_begin_ctx
        return mock_engine, mock_conn

    @pytest.mark.asyncio
    @patch("schema.init_database._build_database_url", return_value="mysql+aiomysql://u:p@h/d")
    @patch("schema.init_database.create_async_engine")
    async def test_views_created(self, mock_create_engine, mock_url):
        """视图创建正常"""
        mock_engine, mock_conn = self._make_engine_mock()
        mock_create_engine.return_value = mock_engine

        from schema.init_database import _create_views_if_needed
        await _create_views_if_needed("mysql")

        assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    @patch("schema.init_database._build_database_url", return_value="mysql+aiomysql://u:p@h/d")
    @patch("schema.init_database.create_async_engine")
    async def test_views_sql_content(self, mock_create_engine, mock_url):
        """验证视图 SQL 包含关键表名"""
        mock_engine, mock_conn = self._make_engine_mock()
        mock_create_engine.return_value = mock_engine

        from schema.init_database import _create_views_if_needed
        await _create_views_if_needed("mysql")

        sql1 = mock_conn.execute.call_args_list[0][0][0].text
        sql2 = mock_conn.execute.call_args_list[1][0][0].text
        assert "daily_topics" in sql1
        assert "crawling_tasks" in sql1
        assert "daily_news" in sql2

    @pytest.mark.asyncio
    @patch("schema.init_database._build_database_url", return_value="mysql+aiomysql://u:p@h/d")
    @patch("schema.init_database.create_async_engine")
    async def test_engine_disposed(self, mock_create_engine, mock_url):
        """引擎被释放"""
        mock_engine, _ = self._make_engine_mock()
        mock_create_engine.return_value = mock_engine

        from schema.init_database import _create_views_if_needed
        await _create_views_if_needed("mysql")

        mock_engine.dispose.assert_called_once()


class TestMain:
    """main 函数"""

    @pytest.mark.asyncio
    @patch("schema.init_database.create_async_engine")
    @patch("schema.init_database.Base")
    @patch("schema.init_database._create_views_if_needed")
    @patch("schema.init_database.settings")
    async def test_main_creates_tables_and_views(self, mock_s, mock_views, mock_base, mock_ce):
        """main 创建表并创建视图"""
        mock_s.DATABASE_URL = None
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_ctx = AsyncMock()
        mock_begin_ctx.__aenter__.return_value = mock_ctx
        mock_engine.begin.return_value = mock_begin_ctx
        mock_ce.return_value = mock_engine
        mock_engine.url.get_backend_name.return_value = "mysql"

        from schema.init_database import main
        await main()

        mock_ctx.run_sync.assert_called_once()
        mock_views.assert_called_once_with("mysql")
        mock_engine.dispose.assert_called_once()
