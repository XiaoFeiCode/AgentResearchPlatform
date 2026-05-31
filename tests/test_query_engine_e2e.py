"""
端到端测试：QueryEngine

使用 mock 替换所有外部依赖（LLM API、搜索 API），
只验证 research() 的外部行为，不依赖内部实现细节。
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# ── 先把项目根路径和 engines/ 加入 sys.path ─────────────────
_proj_root = Path(__file__).resolve().parent.parent
for _p in [str(_proj_root), str(_proj_root / "engines")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── 预注册 retry_helper 模块 ─────────────────────────────────
import types as _types
_retry_helper = _types.ModuleType("retry_helper")
_retry_helper.with_graceful_retry = lambda config=None, default_return=None: (
    lambda f: f
)
_retry_helper.SEARCH_API_RETRY_CONFIG = None
sys.modules["retry_helper"] = _retry_helper


# ── 辅助函数：构造假的 TavilyResponse ─────────────────────────

def _fake_tavily_response() -> "TavilyResponse":
    from QueryEngine.tools.search import TavilyResponse, SearchResult
    return TavilyResponse(
        query="test",
        results=[
            SearchResult(
                title=f"新闻标题{i}",
                url=f"https://news.example.com/{i}",
                content=f"这是第{i}条新闻的内容摘要。",
                score=0.95 - i * 0.1,
                published_date="2026-05-08",
            )
            for i in range(1, 4)
        ],
    )


_AGENT_CONFIG = {
    "QUERY_ENGINE_API_KEY": "sk-test-fake-key",
    "QUERY_ENGINE_MODEL_NAME": "test-model",
    "QUERY_ENGINE_BASE_URL": "https://test.api.com",
    "TAVILY_API_KEY": "test-tavily-key",
    "MAX_REFLECTIONS": 2,
    "SEARCH_CONTENT_MAX_LENGTH": 20000,
}

_LLM_RESPONSES = [
    # 1. ReportStructureNode
    json.dumps([
        {"title": "热点追踪", "content": "追踪当前热点事件"},
        {"title": "深度解读", "content": "深度解读事件背景"},
    ], ensure_ascii=False),
    # 2. FirstSearchNode (段落1)
    json.dumps({"search_query": "热点事件 最新", "search_tool": "basic_search_news", "reasoning": "获取最新热点"}, ensure_ascii=False),
    # 3. FirstSummaryNode (段落1)
    json.dumps({"paragraph_latest_state": "## 热点追踪\n当前热点事件概述。"}, ensure_ascii=False),
    # 4. ReflectionNode (段落1 - 第1轮)
    json.dumps({"search_query": "热点 进展", "search_tool": "search_news_last_24_hours", "reasoning": "补充最新进展"}, ensure_ascii=False),
    # 5. ReflectionSummaryNode (段落1 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 热点追踪（更新）\n事件有新进展。"}, ensure_ascii=False),
    # 6. ReflectionNode (段落1 - 第2轮)
    json.dumps({"search_query": "热点 影响", "search_tool": "search_news_last_week", "reasoning": "分析影响"}, ensure_ascii=False),
    # 7. ReflectionSummaryNode (段落1 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 热点追踪（最终）\n影响范围扩大。"}, ensure_ascii=False),
    # 8. FirstSearchNode (段落2)
    json.dumps({"search_query": "事件背景 分析", "search_tool": "deep_search_news", "reasoning": "深度搜索背景"}, ensure_ascii=False),
    # 9. FirstSummaryNode (段落2)
    json.dumps({"paragraph_latest_state": "## 深度解读\n事件背景复杂。"}, ensure_ascii=False),
    # 10. ReflectionNode (段落2 - 第1轮)
    json.dumps({"search_query": "背景 补充", "search_tool": "search_news_by_date", "reasoning": "按日期搜索"}, ensure_ascii=False),
    # 11. ReflectionSummaryNode (段落2 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 深度解读（更新）\n更多背景信息。"}, ensure_ascii=False),
    # 12. ReflectionNode (段落2 - 第2轮)
    json.dumps({"search_query": "未来趋势", "search_tool": "search_images_for_news", "reasoning": "搜索相关图片"}, ensure_ascii=False),
    # 13. ReflectionSummaryNode (段落2 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 深度解读（最终）\n趋势分析完成。"}, ensure_ascii=False),
    # 14. ReportFormattingNode
    "# 深度研究报告\n\n## 热点追踪\n当前热点事件概述。\n\n## 深度解读\n事件背景复杂。",
]


@pytest.fixture
def agent():
    """创建 mock 好外部依赖的 QueryEngine runner。"""
    responses = list(_LLM_RESPONSES)
    call_count = 0

    def _fake_llm(system_prompt: str, message: str) -> str:
        nonlocal call_count
        call_count += 1
        idx = call_count - 1
        return responses[idx] if idx < len(responses) else "{}"

    from types import SimpleNamespace
    from QueryEngine.agent import run_research
    from QueryEngine.llms import LLMClient
    from QueryEngine.utils.config import Settings
    from QueryEngine.tools import TavilyNewsAgency

    config = Settings(OUTPUT_DIR="/tmp/test_query_reports", **_AGENT_CONFIG)
    llm_client = LLMClient(
        api_key=config.QUERY_ENGINE_API_KEY,
        model_name=config.QUERY_ENGINE_MODEL_NAME,
        base_url=config.QUERY_ENGINE_BASE_URL,
    )
    search_agency = TavilyNewsAgency(api_key=config.TAVILY_API_KEY)

    patches = [
        patch("QueryEngine.llms.base.LLMClient.stream_invoke_to_string", side_effect=_fake_llm),
        patch("QueryEngine.context.QueryContext.execute_search", return_value=_fake_tavily_response()),
    ]
    for p in patches:
        p.start()

    runner = SimpleNamespace()
    runner.config = config
    runner.llm_client = llm_client
    runner.progress_callback = None
    runner.research = lambda query, save_report=True: run_research(
        query, config, llm_client, search_agency, runner.progress_callback, save_report,
    )

    yield runner

    for p in patches:
        p.stop()


class TestQueryEngineBehavior:
    """QueryEngine 行为级端到端测试，只验证外部契约。"""

    def test_research_returns_non_empty_markdown(self, agent):
        result = agent.research("测试查询", save_report=False)
        report = result["final_report"]
        assert report and isinstance(report, str) and len(report) > 0
        assert report.startswith("#")

    def test_research_with_chinese_query(self, agent):
        result = agent.research("中美贸易最新动态", save_report=False)
        assert result["final_report"] and len(result["final_report"]) > 0

    def test_research_save_report_creates_file(self, agent, tmp_path):
        agent.config.OUTPUT_DIR = str(tmp_path)
        result = agent.research("测试保存")
        report = result["final_report"]
        assert report
        md_files = [f for f in tmp_path.iterdir() if f.suffix == ".md"]
        assert len(md_files) > 0
        assert md_files[0].read_text(encoding="utf-8") == report

    def test_search_failure_propagates_error(self, agent):
        from unittest.mock import patch
        with patch("QueryEngine.context.QueryContext.execute_search", side_effect=RuntimeError("Tavily API unreachable")):
            with pytest.raises(RuntimeError):
                agent.research("测试", save_report=False)

    def test_llm_garbage_still_returns_report(self, agent):
        llm_patch = patch.object(agent.llm_client, "stream_invoke_to_string", return_value="一段无法解析的文本。")
        llm_patch.start()
        try:
            result = agent.research("测试", save_report=False)
            assert result["final_report"] and isinstance(result["final_report"], str) and len(result["final_report"]) > 0
        finally:
            llm_patch.stop()

    def test_progress_callback_receives_events(self, agent):
        events = []
        agent.progress_callback = events.append
        result = agent.research("测试查询")
        assert result["final_report"]
        statuses = [e.get("status") for e in events if "status" in e]
        assert "structure" in statuses
        assert "processing" in statuses
        assert "finalizing" in statuses
