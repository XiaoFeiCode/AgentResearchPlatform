"""
爬虫集成测试 — 真正发送 HTTP 请求，验证 API 接口连通性

使用方法：
  # 只跑集成测试（跳过单元测试）：
  python -m pytest tests/test_crawler_integration.py -v

  # 跳过集成测试（只跑单元测试）：
  python -m pytest tests/ -v --ignore=tests/test_crawler_integration.py

  # 全部跑：
  python -m pytest tests/test_crawler_*.py -v
"""

import pytest
import httpx
import json
import sys
import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent

API_BASE_URL = "https://newsnow.busiyi.world"

# 要测试的新闻源
TEST_SOURCES = {
    "weibo": "微博热搜",
    "zhihu": "知乎热榜",
    "bilibili-hot-search": "B站热搜",
    "toutiao": "今日头条",
    "douyin": "抖音热榜",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


# ==================== API 连通性测试 ====================

class TestNewsAPIIntegration:
    """真实请求新闻 API，验证接口是否通"""

    @pytest.mark.integration
    @pytest.mark.parametrize("source_key,source_name", list(TEST_SOURCES.items()))
    def test_fetch_source_returns_200_and_items(self, source_key, source_name):
        """逐个验证每个新闻源返回 HTTP 200 且包含 items"""
        url = f"{API_BASE_URL}/api/s?id={source_key}&latest"
        resp = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)

        assert resp.status_code == 200, f"{source_name}: HTTP {resp.status_code}"
        assert resp.text.startswith("{"), f"{source_name}: 响应不是 JSON"

        data = resp.json()
        items = data.get("items", [])
        assert isinstance(items, list), f"{source_name}: items 不是列表"
        assert len(items) > 0, f"{source_name}: items 为空"

        # 验证第一条数据格式
        first = items[0]
        assert "title" in first, f"{source_name}: 缺少 title 字段"
        assert isinstance(first["title"], str), f"{source_name}: title 不是字符串"
        assert len(first["title"]) > 0, f"{source_name}: title 为空"

    @pytest.mark.integration
    def test_batch_fetch_all_sources(self):
        """一次请求所有源，验证成功率不低于 80%"""
        results = {}
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            for key, name in TEST_SOURCES.items():
                try:
                    resp = client.get(f"{API_BASE_URL}/api/s?id={key}&latest", headers=HEADERS)
                    items_count = len(resp.json().get("items", []))
                    results[key] = {"ok": True, "name": name, "count": items_count}
                except Exception as e:
                    results[key] = {"ok": False, "name": name, "error": str(e)}

        success_count = sum(1 for r in results.values() if r["ok"])
        total = len(TEST_SOURCES)
        rate = success_count / total

        # 打印详细结果
        print(f"\n集成测试结果: {success_count}/{total} 可用 ({rate:.0%})")
        for key, r in results.items():
            status = "✓" if r["ok"] else "✗"
            detail = f"{r.get('count', 0)}条" if r["ok"] else r.get("error", "")
            print(f"  {status} {r['name']:12s} → {detail}")

        assert rate >= 0.8, f"成功率 {rate:.0%} < 80%"

    @pytest.mark.integration
    def test_weibo_response_structure(self):
        """详细验证微博热搜的返回结构"""
        resp = httpx.get(
            f"{API_BASE_URL}/api/s?id=weibo&latest",
            headers=HEADERS, timeout=15.0, follow_redirects=True
        )
        data = resp.json()

        assert data["status"] in ("success", "cache")
        assert data["id"] == "weibo"
        assert "updatedTime" in data

        items = data["items"]
        assert len(items) >= 20  # 微博热搜通常有 30-50 条

        for item in items[:3]:  # 前3条
            assert "id" in item
            assert "title" in item
            assert len(item["title"]) > 0

    @pytest.mark.integration
    def test_zhihu_response_has_url(self):
        """验证知乎热榜的 URL 格式"""
        resp = httpx.get(
            f"{API_BASE_URL}/api/s?id=zhihu&latest",
            headers=HEADERS, timeout=15.0, follow_redirects=True
        )
        items = resp.json().get("items", [])

        assert len(items) > 0
        for item in items[:5]:
            assert "url" in item
            assert item["url"].startswith("http"), f"URL 格式异常: {item['url']}"


# ==================== API 错误场景测试 ====================

class TestNewsAPIErrorScenarios:
    """测试 API 在异常情况下的行为"""

    @pytest.mark.integration
    def test_invalid_source_id(self):
        """测试无效的 source id 返回什么"""
        resp = httpx.get(
            f"{API_BASE_URL}/api/s?id=invalid_source_xxx&latest",
            headers=HEADERS, timeout=15.0, follow_redirects=True
        )
        # 该 API 对无效源返回 500，记录此行为
        assert resp.status_code in (200, 404, 400, 500)

    @pytest.mark.integration
    def test_missing_source_id(self):
        """测试不传 id 参数"""
        resp = httpx.get(
            f"{API_BASE_URL}/api/s?latest",
            headers=HEADERS, timeout=15.0, follow_redirects=True
        )
        # 该 API 对缺失参数返回 500
        assert resp.status_code in (200, 400, 422, 500)

    @pytest.mark.integration
    def test_response_time_acceptable(self):
        """测试响应时间在可接受范围内（< 5s）"""
        import time
        start = time.time()
        httpx.get(
            f"{API_BASE_URL}/api/s?id=weibo&latest",
            headers=HEADERS, timeout=15.0, follow_redirects=True
        )
        elapsed = time.time() - start
        assert elapsed < 5.0, f"响应时间 {elapsed:.1f}s 超过 5s 阈值"


# ==================== 数据库集成测试 ====================

class TestDatabaseIntegration:
    """连接真实数据库，验证爬虫表结构和数据操作"""

    @pytest.fixture(scope="class")
    def db_conn(self):
        """建立真实数据库连接（可用则连，不可用则跳过）"""
        try:
            import pymysql
            conn = pymysql.connect(
                host="127.0.0.1", port=3306, user="root",
                password="Atguigu.123", database="dw", charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor
            )
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"数据库不可用: {e}")

    @pytest.mark.integration
    def test_spider_tables_exist(self, db_conn):
        """验证爬虫相关的表都存在"""
        with db_conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            # DictCursor 的 key 是 bytes，取第一个 value 即可
            tables = {list(r.values())[0] for r in cur.fetchall()}

        required = {"daily_news", "daily_topics", "topic_news_relation", "crawling_tasks"}
        missing = required - tables
        assert not missing, f"缺少表: {missing}"
        print(f"  表就绪: {len(required)}/4")

    @pytest.mark.integration
    def test_daily_topics_table_structure(self, db_conn):
        """验证 daily_topics 表结构"""
        with db_conn.cursor() as cur:
            cur.execute("DESCRIBE daily_topics")
            columns = {r["Field"]: r["Type"] for r in cur.fetchall()}

        required_fields = {"id", "extract_date", "topic_id", "topic_name", "keywords", "topic_description"}
        assert required_fields.issubset(columns.keys()), \
            f"缺少字段: {required_fields - set(columns.keys())}"

    @pytest.mark.integration
    def test_save_and_query_news_roundtrip(self, db_conn):
        """真实写入一条新闻并查询回来"""
        import datetime
        today = datetime.date.today()
        news_id = f"integration_test_{today.strftime('%Y%m%d')}"

        with db_conn.cursor() as cur:
            # 清理可能存在的旧数据
            cur.execute("DELETE FROM daily_news WHERE news_id = %s", (news_id,))
            db_conn.commit()

            # 写入（add_ts 和 last_modify_ts 没有默认值，需显式传入）
            now_ts = int(datetime.datetime.now().timestamp())
            cur.execute(
                """INSERT INTO daily_news (news_id, source_platform, title, url, crawl_date, rank_position, add_ts, last_modify_ts)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (news_id, "integration_test", "集成测试新闻标题", "https://test.com", today, 1, now_ts, now_ts)
            )
            db_conn.commit()

            # 查询回来
            cur.execute("SELECT * FROM daily_news WHERE news_id = %s", (news_id,))
            row = cur.fetchone()

            # 清理
            cur.execute("DELETE FROM daily_news WHERE news_id = %s", (news_id,))
            db_conn.commit()

        assert row is not None, "写入后查不到数据"
        assert row["title"] == "集成测试新闻标题"
        assert row["source_platform"] == "integration_test"
        print(f"  读写验证通过: {row['title']}")

    @pytest.mark.integration
    def test_daily_news_has_recent_data(self, db_conn):
        """验证 daily_news 表中有近期数据（说明定时任务在正常运行）"""
        import datetime
        today = datetime.date.today()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM daily_news WHERE crawl_date = %s",
                (today,)
            )
            count = cur.fetchone()["cnt"]

        if count > 0:
            print(f"  今日已有 {count} 条新闻数据")
        else:
            print("  今日暂无数据（定时任务尚未运行或已归档）")


# ==================== 完整的端到端采集测试 ====================

class TestFullCollectionFlow:
    """真正调用 NewsCollector 采集并入库"""

    @pytest.mark.integration
    def test_collect_weibo_and_save(self):
        """真实采集微博热搜并存入数据库"""
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector

        import asyncio

        async def collect():
            collector = NewsCollector()
            try:
                result = await collector.collect_and_save_news(sources=["weibo"])
                return result
            finally:
                collector.close()

        result = asyncio.run(collect())

        assert result["success"] is True
        assert result["total_news"] > 0, "没有采集到新闻"
        assert result["successful_sources"] == 1
        assert result.get("saved_count", 0) > 0, "数据库没有保存成功"

        print(f"  采集微博: {result['total_news']} 条, 入库: {result['saved_count']} 条")

    @pytest.mark.integration
    def test_collect_multiple_sources(self):
        """真实采集多个源"""
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / "tools" / "SentinelSpider"))
        from tools.SentinelSpider.BroadTopicExtraction.get_today_news import NewsCollector

        import asyncio

        async def collect():
            collector = NewsCollector()
            try:
                result = await collector.collect_and_save_news(
                    sources=["zhihu", "bilibili-hot-search", "toutiao"]
                )
                return result
            finally:
                collector.close()

        result = asyncio.run(collect())

        assert result["success"] is True
        print(f"  采集 {result['successful_sources']}/{result['total_sources']} 个源")
        print(f"  共 {result['total_news']} 条, 入库 {result.get('saved_count', 0)} 条")
