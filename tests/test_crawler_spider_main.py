"""
测试 SentinelSpider/main.py — 核心编排 & CLI

覆盖 SentinelSpider 类的所有方法以及 main() CLI 入口
"""

from pathlib import Path

project_root = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from datetime import date


# ==================== Fixtures ====================

@pytest.fixture
def spider():
    """创建 SentinelSpider 实例（不依赖真实环境）"""
    from tools.SentinelSpider.main import SentinelSpider
    return SentinelSpider()


@pytest.fixture
def mock_settings():
    """提供完整的 settings mock"""
    s = MagicMock()
    s.DB_HOST = "localhost"
    s.DB_PORT = 3306
    s.DB_USER = "root"
    s.DB_PASSWORD = "pass"
    s.DB_NAME = "dw"
    s.DB_CHARSET = "utf8mb4"
    s.DB_DIALECT = "mysql"
    s.SENTINEL_SPIDER_API_KEY = "sk-test"
    s.SENTINEL_SPIDER_BASE_URL = "https://api.deepseek.com/v1"
    s.SENTINEL_SPIDER_MODEL_NAME = "deepseek-chat"
    return s


# ==================== 配置检查 ====================

class TestConfig:
    """check_config 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_all_configs_present(self, mock_s, spider):
        """所有必需配置都存在 → 通过"""
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8"
        mock_s.SENTINEL_SPIDER_API_KEY = "key"
        mock_s.SENTINEL_SPIDER_BASE_URL = "url"
        mock_s.SENTINEL_SPIDER_MODEL_NAME = "model"

        assert spider.check_config() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_missing_db_host(self, mock_s, spider):
        """缺少 DB_HOST → 失败"""
        mock_s.DB_HOST = ""
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8"
        mock_s.SENTINEL_SPIDER_API_KEY = "key"
        mock_s.SENTINEL_SPIDER_BASE_URL = "url"
        mock_s.SENTINEL_SPIDER_MODEL_NAME = "model"

        assert spider.check_config() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_missing_api_key(self, mock_s, spider):
        """缺少 SENTINEL_SPIDER_API_KEY → 失败"""
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8"
        mock_s.SENTINEL_SPIDER_API_KEY = None
        mock_s.SENTINEL_SPIDER_BASE_URL = "url"
        mock_s.SENTINEL_SPIDER_MODEL_NAME = "model"

        assert spider.check_config() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_missing_all_configs(self, mock_s, spider):
        """所有配置都缺失 → 失败"""
        mock_s.DB_HOST = None
        mock_s.DB_PORT = None
        mock_s.DB_USER = None
        mock_s.DB_PASSWORD = None
        mock_s.DB_NAME = None
        mock_s.DB_CHARSET = None
        mock_s.SENTINEL_SPIDER_API_KEY = None
        mock_s.SENTINEL_SPIDER_BASE_URL = None
        mock_s.SENTINEL_SPIDER_MODEL_NAME = None

        assert spider.check_config() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_config_hasattr_false_for_missing(self, mock_s, spider):
        """settings 对象根本没有某属性 → 失败"""
        # MagicMock 默认返回新 MagicMock 对于未设置属性，所以 hasattr 永远 True
        # 但实际代码里 hasattr 返回 True（MagicMock 特性），用 getattr 检测空字符串
        mock_s.DB_HOST = ""
        del mock_s.DB_PORT  # 这会怎样？MagicMock 不会真的删除
        # MagicMock 的 hasattr 永远 True，所以这里用空值检测
        mock_s.DB_HOST = mock_s.DB_USER = mock_s.DB_PASSWORD = ""
        mock_s.DB_NAME = mock_s.DB_CHARSET = ""
        mock_s.DB_PORT = ""
        mock_s.SENTINEL_SPIDER_API_KEY = ""
        mock_s.SENTINEL_SPIDER_BASE_URL = ""
        mock_s.SENTINEL_SPIDER_MODEL_NAME = ""

        assert spider.check_config() is False


# ==================== 数据库连接检查 ====================

class TestDBConnection:
    """check_database_connection 方法"""

def _make_async_engine_success():
    """创建模拟成功连接的异步引擎。"""
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_ctx = AsyncMock()  # __aenter__/__aexit__ 自动配置
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()   # await conn.execute(...)
    mock_conn.run_sync = AsyncMock()  # await conn.run_sync(...)
    # run_sync 需实际执行函数，让 _get_tables(sync_conn) 内部调 inspect(conn)
    mock_conn.run_sync.side_effect = lambda fn, *a, **kw: fn(mock_conn)
    mock_ctx.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value = mock_ctx
    return mock_engine

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_connection_success(self, mock_s, mock_create_engine, spider):
        """连接成功 → True"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_create_engine.return_value = _make_async_engine_success()

        assert spider.check_database_connection() is True
        # 验证 URL 包含了正确的参数
        url_arg = mock_create_engine.call_args[0][0]
        assert "charset=utf8mb4" in url_arg

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_connection_failure(self, mock_s, mock_create_engine, spider):
        """连接失败 → False"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        # connect 时抛出异常
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("connection refused")
        mock_engine.dispose = AsyncMock()
        mock_create_engine.return_value = mock_engine

        assert spider.check_database_connection() is False

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_postgresql_dialect_url(self, mock_s, mock_create_engine, spider):
        """PostgreSQL dialect 构建正确的 URL"""
        mock_s.DB_DIALECT = "postgresql"
        mock_s.DB_HOST = "pg_host"
        mock_s.DB_PORT = 5432
        mock_s.DB_USER = "pg_user"
        mock_s.DB_PASSWORD = "pg_pass"
        mock_s.DB_NAME = "pg_db"
        mock_s.DB_CHARSET = "utf8"

        mock_create_engine.return_value = _make_async_engine_success()

        assert spider.check_database_connection() is True
        url_arg = mock_create_engine.call_args[0][0]
        assert "postgresql+asyncpg://pg_user:pg_pass@pg_host:5432/pg_db" in url_arg

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_mysql_url_with_charset(self, mock_s, mock_create_engine, spider):
        """MySQL URL 包含 charset 参数"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "my_host"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "my_user"
        mock_s.DB_PASSWORD = "my_pass"
        mock_s.DB_NAME = "my_db"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_create_engine.return_value = _make_async_engine_success()

        assert spider.check_database_connection() is True
        url_arg = mock_create_engine.call_args[0][0]
        assert "mysql+asyncmy://my_user:my_pass@my_host:3306/my_db?charset=utf8mb4" in url_arg

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_password_with_special_chars_encoded(self, mock_s, mock_create_engine, spider):
        """密码含特殊字符时 URL-encoded"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p@ss!w#rd"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_create_engine.return_value = _make_async_engine_success()

        assert spider.check_database_connection() is True
        url_arg = mock_create_engine.call_args[0][0]
        assert "p%40ss%21w%23rd" in url_arg  # URL-encoded


# ==================== 数据库表检查 ====================

class TestDBTables:
    """check_database_tables 方法"""

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.inspect")
    @patch("tools.SentinelSpider.main.settings")
    def test_all_tables_exist(self, mock_s, mock_inspect, mock_create, spider):
        """所有必需表存在 → True"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_create.return_value = _make_async_engine_success()
        mock_inspect.return_value.get_table_names.return_value = ["daily_news", "daily_topics"]
        assert spider.check_database_tables() is True

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.inspect")
    @patch("tools.SentinelSpider.main.settings")
    def test_missing_daily_topics(self, mock_s, mock_inspect, mock_engine, spider):
        """缺少 daily_topics → False"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_engine.return_value = _make_async_engine_success()
        mock_inspect.return_value.get_table_names.return_value = ["daily_news"]
        assert spider.check_database_tables() is False

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.inspect")
    @patch("tools.SentinelSpider.main.settings")
    def test_no_tables_at_all(self, mock_s, mock_inspect, mock_engine, spider):
        """没有任何表 → False"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_engine.return_value = _make_async_engine_success()
        mock_inspect.return_value.get_table_names.return_value = []
        assert spider.check_database_tables() is False

    @patch("tools.SentinelSpider.main.create_async_engine")
    @patch("tools.SentinelSpider.main.settings")
    def test_inspect_raises_exception(self, mock_s, mock_engine, spider):
        """数据库异常 → False"""
        mock_s.DB_DIALECT = "mysql"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_NAME = "d"
        mock_s.DB_CHARSET = "utf8mb4"

        mock_engine.return_value = _make_async_engine_success()
        # 让 run_sync 抛异常
        mock_engine.return_value.connect.return_value.__aenter__.return_value.run_sync.side_effect = Exception("inspect error")

        assert spider.check_database_tables() is False


# ==================== 数据库初始化 ====================

class TestInitDB:
    """initialize_database 方法"""

    @patch("tools.SentinelSpider.main.subprocess.run")
    @patch("tools.SentinelSpider.main.settings")
    def test_init_success(self, mock_s, mock_run, spider):
        """子进程返回 0 → True"""
        mock_s.DB_NAME = "dw"
        mock_s.DB_HOST = "h"
        mock_s.DB_PORT = 3306
        mock_s.DB_USER = "u"
        mock_s.DB_PASSWORD = "p"
        mock_s.DB_CHARSET = "utf8mb4"
        mock_s.SENTINEL_SPIDER_API_KEY = "k"
        mock_s.SENTINEL_SPIDER_BASE_URL = "u"
        mock_s.SENTINEL_SPIDER_MODEL_NAME = "m"

        mock_run.return_value = MagicMock(returncode=0)

        assert spider.initialize_database() is True
        # 验证调用了子进程
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "init_database.py" in str(cmd)

    @patch("tools.SentinelSpider.main.subprocess.run")
    @patch("tools.SentinelSpider.main.settings")
    def test_init_failure(self, mock_s, mock_run, spider):
        """子进程返回非 0 → False"""
        mock_s.DB_NAME = "dw"

        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        assert spider.initialize_database() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_init_timeout(self, mock_s, spider):
        """子进程超时 → False"""
        import subprocess
        mock_s.DB_NAME = "dw"
        spider.schema_path = MagicMock()
        spider.schema_path.__truediv__.return_value.exists.return_value = True

        with patch("tools.SentinelSpider.main.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="init", timeout=300)):
            assert spider.initialize_database() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_init_script_not_found(self, mock_s, spider):
        """初始化脚本文件不存在 → False"""
        mock_s.DB_NAME = "dw"
        # mock 掉整个 schema_path，使文件不存在
        spider.schema_path = MagicMock()
        spider.schema_path.__truediv__.return_value.exists.return_value = False

        assert spider.initialize_database() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_init_passes_db_name_env(self, mock_s, spider):
        """initialize_database 传递 DB_NAME 环境变量给子进程"""
        mock_s.DB_NAME = "test_db"
        import subprocess

        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("tools.SentinelSpider.main.subprocess.run", mock_run):
            spider.initialize_database()

        env = mock_run.call_args[1].get("env", {})
        assert env.get("DB_NAME") == "test_db"


# ==================== 确保数据库就绪 ====================

class TestEnsureDB:
    """_ensure_database_ready 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_db_ready(self, mock_s, spider):
        """数据库连接正常且表存在 → True"""
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=True)

        assert spider._ensure_database_ready() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_db_connect_fails(self, mock_s, spider):
        """数据库连接失败 → False（不继续检查表）"""
        spider.check_database_connection = MagicMock(return_value=False)
        spider.check_database_tables = MagicMock()

        assert spider._ensure_database_ready() is False
        spider.check_database_tables.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_tables_missing_then_init_ok(self, mock_s, spider):
        """表缺失后自动初始化成功 → True"""
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=False)
        spider.initialize_database = MagicMock(return_value=True)

        assert spider._ensure_database_ready() is True
        spider.initialize_database.assert_called_once()

    @patch("tools.SentinelSpider.main.settings")
    def test_tables_missing_then_init_fails(self, mock_s, spider):
        """表缺失后初始化失败 → False"""
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=False)
        spider.initialize_database = MagicMock(return_value=False)

        assert spider._ensure_database_ready() is False


# ==================== 依赖检查 ====================

class TestDependencies:
    """check_dependencies 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_all_deps_ok(self, mock_s, spider):
        """所有依赖都存在 → True"""
        with patch("tools.SentinelSpider.main.Path.exists", return_value=True):
            with patch("builtins.__import__") as mock_import:
                mock_import.return_value = MagicMock()
                with patch.object(spider, "_install_mediacrawler_dependencies", return_value=True):
                    assert spider.check_dependencies() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_missing_pymysql(self, mock_s, spider):
        """缺少 pymysql → False"""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pymysql":
                raise ImportError("no pymysql")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with patch("tools.SentinelSpider.main.Path.exists", return_value=True):
                assert spider.check_dependencies() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_missing_playwright(self, mock_s, spider):
        """缺少 playwright → False"""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "playwright":
                raise ImportError("no playwright")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with patch("tools.SentinelSpider.main.Path.exists", return_value=True):
                assert spider.check_dependencies() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_mediacrawler_dir_missing(self, mock_s, spider):
        """MediaCrawler 目录不存在 → False"""
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = MagicMock()
            # 替换 deep_sentiment_path 为 mock，使其 / "MediaCrawler" 返回 mock
            mock_path = MagicMock()
            mock_mediacrawler = MagicMock()
            mock_mediacrawler.exists.return_value = False  # MediaCrawler 不存在
            mock_path.__truediv__.return_value = mock_mediacrawler
            spider.deep_sentiment_path = mock_path
            assert spider.check_dependencies() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_install_mediacrawler_deps(self, mock_s, spider):
        """_install_mediacrawler_dependencies 正常"""
        import subprocess
        # 需要 mock stat() 和 exists()，因为代码先 stat 比较 mtime，再检查 exists
        with patch("tools.SentinelSpider.main.Path.exists", return_value=True):
            with patch("tools.SentinelSpider.main.Path.stat") as mock_stat:
                mock_stat.return_value.st_mtime = 1000
                with patch("tools.SentinelSpider.main.subprocess.run",
                           return_value=MagicMock(returncode=0)):
                    result = spider._install_mediacrawler_dependencies()
                    assert result is True


# ==================== 话题提取模块执行 ====================

class TestBroadTopic:
    """run_broad_topic_extraction 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_run_success(self, mock_s, spider):
        """子进程成功 → True"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        import subprocess
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)):
            assert spider.run_broad_topic_extraction() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_run_subprocess_fails(self, mock_s, spider):
        """子进程失败 → False"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=1)):
            assert spider.run_broad_topic_extraction() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_ensure_db_fails(self, mock_s, spider):
        """数据库未就绪 → 不执行子进程"""
        spider._ensure_database_ready = MagicMock(return_value=False)

        with patch("tools.SentinelSpider.main.subprocess.run") as mock_run:
            assert spider.run_broad_topic_extraction() is False
            mock_run.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_keywords_count_passed(self, mock_s, spider):
        """验证 --keywords 参数传递"""
        spider._ensure_database_ready = MagicMock(return_value=True)

        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_broad_topic_extraction(keywords_count=50)
            cmd = mock_run.call_args[0][0]
            assert "--keywords" in cmd
            assert "50" in cmd

    @patch("tools.SentinelSpider.main.settings")
    def test_date_not_passed_to_subprocess(self, mock_s, spider):
        """验证 --date 没有传递给子进程（已知 bug）"""
        spider._ensure_database_ready = MagicMock(return_value=True)

        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_broad_topic_extraction(extract_date=date(2026, 5, 6))
            cmd = " ".join(mock_run.call_args[0][0])
            assert "--date" not in cmd  # 日期参数被忽略 — 已知问题


# ==================== 情感爬取模块执行 ====================

class TestDeepSentiment:
    """run_deep_sentiment_crawling 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_run_success(self, mock_s, spider):
        """子进程成功 → True"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)):
            assert spider.run_deep_sentiment_crawling() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_run_failure(self, mock_s, spider):
        """子进程失败 → False"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=1)):
            assert spider.run_deep_sentiment_crawling() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_platforms_passed(self, mock_s, spider):
        """验证 --platforms 参数传递"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_deep_sentiment_crawling(platforms=["xhs", "wb"])
            cmd = mock_run.call_args[0][0]
            assert "--platforms" in cmd
            assert "xhs" in cmd
            assert "wb" in cmd

    @patch("tools.SentinelSpider.main.settings")
    def test_test_mode_flag(self, mock_s, spider):
        """验证 --test 参数传递"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_deep_sentiment_crawling(test_mode=True)
            cmd = mock_run.call_args[0][0]
            assert "--test" in cmd

    @patch("tools.SentinelSpider.main.settings")
    def test_default_max_values(self, mock_s, spider):
        """验证默认 max_keywords/max_notes 值"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_deep_sentiment_crawling()
            cmd = " ".join(mock_run.call_args[0][0])
            assert "--max-keywords 50" in cmd
            assert "--max-notes 50" in cmd

    @patch("tools.SentinelSpider.main.settings")
    def test_custom_date_passed(self, mock_s, spider):
        """验证 --date 参数传递（DeepSentiment 传递了日期，和 BroadTopic 不同）"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        with patch("tools.SentinelSpider.main.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            spider.run_deep_sentiment_crawling(target_date=date(2026, 5, 1))
            cmd = " ".join(mock_run.call_args[0][0])
            assert "--date 2026-05-01" in cmd


# ==================== 完整工作流 ====================

class TestCompleteWorkflow:
    """run_complete_workflow 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_both_steps_succeed(self, mock_s, spider):
        """两步都成功 → True"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        spider.run_broad_topic_extraction = MagicMock(return_value=True)
        spider.run_deep_sentiment_crawling = MagicMock(return_value=True)

        assert spider.run_complete_workflow() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_broad_topic_fails(self, mock_s, spider):
        """第一步失败 → False（不执行第二步）"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        spider.run_broad_topic_extraction = MagicMock(return_value=False)
        spider.run_deep_sentiment_crawling = MagicMock()

        assert spider.run_complete_workflow() is False
        spider.run_deep_sentiment_crawling.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_deep_sentiment_fails(self, mock_s, spider):
        """第二步失败 → False"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        spider.run_broad_topic_extraction = MagicMock(return_value=True)
        spider.run_deep_sentiment_crawling = MagicMock(return_value=False)

        assert spider.run_complete_workflow() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_ensure_db_fails(self, mock_s, spider):
        """数据库检查失败 → False（不执行任何步骤）"""
        spider._ensure_database_ready = MagicMock(return_value=False)

        assert spider.run_complete_workflow() is False

    @patch("tools.SentinelSpider.main.settings")
    def test_arguments_passed_to_substeps(self, mock_s, spider):
        """验证参数正确传递给子步骤"""
        spider._ensure_database_ready = MagicMock(return_value=True)
        spider.run_broad_topic_extraction = MagicMock(return_value=True)
        spider.run_deep_sentiment_crawling = MagicMock(return_value=True)

        spider.run_complete_workflow(
            target_date=date(2026, 5, 1),
            platforms=["xhs"],
            keywords_count=80,
            max_keywords=30,
            max_notes=20,
            test_mode=True
        )

        spider.run_broad_topic_extraction.assert_called_with(date(2026, 5, 1), 80)
        spider.run_deep_sentiment_crawling.assert_called_with(
            date(2026, 5, 1), ["xhs"], 30, 20, True
        )


# ==================== 状态显示 ====================

class TestStatus:
    """show_status 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_status_all_ok(self, mock_s, spider):
        """所有组件正常 → 不抛异常"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=True)
        spider.check_dependencies = MagicMock(return_value=True)

        # 只是验证不抛异常（show_status 没有返回值）
        spider.show_status()

    @patch("tools.SentinelSpider.main.settings")
    def test_status_config_fails(self, mock_s, spider):
        """配置失败时不检查数据库"""
        spider.check_config = MagicMock(return_value=False)
        spider.check_database_connection = MagicMock()

        spider.show_status()
        spider.check_database_connection.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_status_db_tables_not_checked_if_connect_fails(self, mock_s, spider):
        """数据库连接失败时不检查表"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_database_connection = MagicMock(return_value=False)
        spider.check_database_tables = MagicMock()

        spider.show_status()
        spider.check_database_tables.assert_not_called()


# ==================== 项目初始化 ====================

class TestSetup:
    """setup_project 方法"""

    @patch("tools.SentinelSpider.main.settings")
    def test_setup_all_ok(self, mock_s, spider):
        """所有步骤成功 → True"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_dependencies = MagicMock(return_value=True)
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=True)

        assert spider.setup_project() is True

    @patch("tools.SentinelSpider.main.settings")
    def test_setup_config_fails(self, mock_s, spider):
        """配置检查失败 → False（不继续）"""
        spider.check_config = MagicMock(return_value=False)
        spider.check_dependencies = MagicMock()

        assert spider.setup_project() is False
        spider.check_dependencies.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_setup_deps_fails(self, mock_s, spider):
        """依赖检查失败 → False"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_dependencies = MagicMock(return_value=False)
        spider.check_database_connection = MagicMock()

        assert spider.setup_project() is False
        spider.check_database_connection.assert_not_called()

    @patch("tools.SentinelSpider.main.settings")
    def test_setup_tables_missing_init_ok(self, mock_s, spider):
        """表缺失后初始化成功 → True"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_dependencies = MagicMock(return_value=True)
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=False)
        spider.initialize_database = MagicMock(return_value=True)

        assert spider.setup_project() is True
        spider.initialize_database.assert_called_once()

    @patch("tools.SentinelSpider.main.settings")
    def test_setup_tables_missing_init_fails(self, mock_s, spider):
        """表缺失且初始化失败 → False"""
        spider.check_config = MagicMock(return_value=True)
        spider.check_dependencies = MagicMock(return_value=True)
        spider.check_database_connection = MagicMock(return_value=True)
        spider.check_database_tables = MagicMock(return_value=False)
        spider.initialize_database = MagicMock(return_value=False)

        assert spider.setup_project() is False


# ==================== CLI 解析 ====================

class TestCLI:
    """main() CLI 入口"""

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_status_flag(self, mock_s, mock_spider_cls):
        """--status 调用 show_status"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--status"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.show_status.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_setup_flag(self, mock_s, mock_spider_cls):
        """--setup 调用 setup_project"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--setup"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.setup_project.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_init_db_flag(self, mock_s, mock_spider_cls):
        """--init-db 调用 initialize_database"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--init-db"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.initialize_database.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_broad_topic_flag(self, mock_s, mock_spider_cls):
        """--broad-topic 调用 run_broad_topic_extraction"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--broad-topic"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_broad_topic_extraction.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_deep_sentiment_flag(self, mock_s, mock_spider_cls):
        """--deep-sentiment 调用 run_deep_sentiment_crawling"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--deep-sentiment"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_deep_sentiment_crawling.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_complete_flag(self, mock_s, mock_spider_cls):
        """--complete 调用 run_complete_workflow"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--complete"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_complete_workflow.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_default_runs_complete_workflow(self, mock_s, mock_spider_cls):
        """没有参数时默认运行完整工作流"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_complete_workflow.assert_called_once()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_platforms_argument(self, mock_s, mock_spider_cls):
        """--platforms 参数传递"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--complete", "--platforms", "xhs", "wb", "--test"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_complete_workflow.assert_called_once()
        args = mock_spider.run_complete_workflow.call_args[0]
        assert args[1] == ["xhs", "wb"]  # platforms at index 1
        assert args[5] is True           # test_mode at index 5

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_test_mode(self, mock_s, mock_spider_cls):
        """--test 开关"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--complete", "--test"]):
            from tools.SentinelSpider.main import main
            main()

        args = mock_spider.run_complete_workflow.call_args[0]
        assert args[5] is True  # test_mode at index 5

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_date_parsing_valid(self, mock_s, mock_spider_cls):
        """--date 格式正确时传递"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--broad-topic", "--date", "2026-05-01"]):
            from tools.SentinelSpider.main import main
            main()

        args, kwargs = mock_spider.run_broad_topic_extraction.call_args
        assert args[0] == date(2026, 5, 1)

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_date_parsing_invalid(self, mock_s, mock_spider_cls):
        """--date 格式错误时记录错误但不崩溃"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        # 无效日期不会调用任何 run 方法
        with patch("sys.argv", ["main.py", "--broad-topic", "--date", "not-a-date"]):
            from tools.SentinelSpider.main import main
            main()

        mock_spider.run_broad_topic_extraction.assert_not_called()

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_keywords_count_override(self, mock_s, mock_spider_cls):
        """--keywords-count 传递到 run_broad_topic_extraction"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", ["main.py", "--broad-topic", "--keywords-count", "200"]):
            from tools.SentinelSpider.main import main
            main()

        args, kwargs = mock_spider.run_broad_topic_extraction.call_args
        assert args[1] == 200  # keywords_count

    @patch("tools.SentinelSpider.main.SentinelSpider")
    @patch("tools.SentinelSpider.main.settings")
    def test_max_keywords_notes(self, mock_s, mock_spider_cls):
        """--max-keywords 和 --max-notes 参数"""
        mock_spider = MagicMock()
        mock_spider_cls.return_value = mock_spider

        with patch("sys.argv", [
            "main.py", "--deep-sentiment",
            "--max-keywords", "10", "--max-notes", "5"
        ]):
            from tools.SentinelSpider.main import main
            main()

        args = mock_spider.run_deep_sentiment_crawling.call_args[0]
        assert args[2] == 10  # max_keywords at index 2
        assert args[3] == 5   # max_notes at index 3
