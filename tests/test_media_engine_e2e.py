"""
端到端测试：MediaEngine

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
# MediaEngine / QueryEngine tools 在 import 时会尝试 from retry_helper import ...，
# 但 engines/utils/ 目录不存在。预注册一个 mock 模块避免导入失败。
import types as _types
_retry_helper = _types.ModuleType("retry_helper")
_retry_helper.with_graceful_retry = lambda config=None, default_return=None: (
    lambda f: f
)
_retry_helper.SEARCH_API_RETRY_CONFIG = None
sys.modules["retry_helper"] = _retry_helper


# ── 辅助函数：构造假的 BochaResponse ─────────────────────────

def _fake_bocha_response() -> "BochaResponse":
    from MediaEngine.tools.search import BochaResponse, WebpageResult
    return BochaResponse(
        query="test",
        answer="模拟的 AI 总结",
        webpages=[
            WebpageResult(
                name=f"搜索结果{i}",
                url=f"https://example.com/{i}",
                snippet=f"这是第{i}条搜索结果的摘要内容。",
            )
            for i in range(1, 4)
        ],
    )


_AGENT_CONFIG = {
    "MEDIA_ENGINE_API_KEY": "sk-test-fake-key",
    "MEDIA_ENGINE_MODEL_NAME": "test-model",
    "MEDIA_ENGINE_BASE_URL": "https://test.api.com",
    "BOCHA_API_KEY": "test-bocha-key",
    "MAX_REFLECTIONS": 2,
    "SEARCH_CONTENT_MAX_LENGTH": 20000,
}

_LLM_RESPONSES = [
    # 1. ReportStructureNode
    json.dumps([
        {"title": "市场概况", "content": "分析市场整体表现"},
        {"title": "竞争格局", "content": "分析主要竞争对手"},
    ], ensure_ascii=False),
    # 2. FirstSearchNode (段落1)
    json.dumps({"search_query": "市场概况 数据", "search_tool": "comprehensive_search", "reasoning": "需要获取市场数据"}, ensure_ascii=False),
    # 3. FirstSummaryNode (段落1)
    json.dumps({"paragraph_latest_state": "## 市场概况\n2025年市场整体表现良好。"}, ensure_ascii=False),
    # 4. ReflectionNode (段落1 - 第1轮)
    json.dumps({"search_query": "市场 最新动态", "search_tool": "search_last_24_hours", "reasoning": "需要补充最新动态"}, ensure_ascii=False),
    # 5. ReflectionSummaryNode (段落1 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 市场概况（更新）\n最新数据显示增长加速。"}, ensure_ascii=False),
    # 6. ReflectionNode (段落1 - 第2轮)
    json.dumps({"search_query": "市场 风险因素", "search_tool": "search_last_week", "reasoning": "需要检查风险"}, ensure_ascii=False),
    # 7. ReflectionSummaryNode (段落1 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 市场概况（最终）\n增长加速，需关注政策风险。"}, ensure_ascii=False),
    # 8. FirstSearchNode (段落2)
    json.dumps({"search_query": "竞争格局 分析", "search_tool": "comprehensive_search", "reasoning": "需要获取竞争数据"}, ensure_ascii=False),
    # 9. FirstSummaryNode (段落2)
    json.dumps({"paragraph_latest_state": "## 竞争格局\n主要竞争对手包括A、B、C三家。"}, ensure_ascii=False),
    # 10. ReflectionNode (段落2 - 第1轮)
    json.dumps({"search_query": "竞争对手 动态", "search_tool": "search_last_24_hours", "reasoning": "需要补充竞品动态"}, ensure_ascii=False),
    # 11. ReflectionSummaryNode (段落2 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 竞争格局（更新）\nA公司推出新产品。"}, ensure_ascii=False),
    # 12. ReflectionNode (段落2 - 第2轮)
    json.dumps({"search_query": "竞争 趋势预测", "search_tool": "search_last_week", "reasoning": "需要分析趋势"}, ensure_ascii=False),
    # 13. ReflectionSummaryNode (段落2 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 竞争格局（最终）\nA公司领先，B公司下滑。"}, ensure_ascii=False),
    # 14. ReportFormattingNode
    "# 深度研究报告\n\n## 市场概况\n2025年市场整体表现良好。\n\n## 竞争格局\n主要竞争对手包括A、B、C三家。",
]


@pytest.fixture
def agent():
    """创建 mock 好外部依赖的 MediaEngine runner。"""
    responses = list(_LLM_RESPONSES)
    call_count = 0

    def _fake_llm(system_prompt: str, message: str) -> str:
        nonlocal call_count
        call_count += 1
        idx = call_count - 1
        return responses[idx] if idx < len(responses) else "{}"

    from types import SimpleNamespace
    from MediaEngine.agent import run_research
    from MediaEngine.llms import LLMClient
    from MediaEngine.utils.config import Settings
    from MediaEngine.tools import BochaMultimodalSearch

    config = Settings(OUTPUT_DIR="/tmp/test_media_reports", **_AGENT_CONFIG)
    llm_client = LLMClient(
        api_key=config.MEDIA_ENGINE_API_KEY,
        model_name=config.MEDIA_ENGINE_MODEL_NAME,
        base_url=config.MEDIA_ENGINE_BASE_URL,
    )
    search_agency = BochaMultimodalSearch(api_key="test-bocha-key")

    patches = [
        patch("MediaEngine.llms.base.LLMClient.stream_invoke_to_string", side_effect=_fake_llm),
        patch("MediaEngine.context.MediaContext.execute_search", return_value=_fake_bocha_response()),
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


class TestMediaEngineBehavior:
    """MediaEngine 行为级端到端测试，只验证外部契约。"""

    def test_research_returns_non_empty_markdown(self, agent):
        """research() 返回非空 Markdown 文本。"""
        result = agent.research("测试查询", save_report=False)
        report = result["final_report"]
        assert report
        assert isinstance(report, str)
        assert len(report) > 50
        assert report.startswith("#"), "报告应以 Markdown 标题开头"

    def test_research_with_chinese_query(self, agent):
        """中文查询正常产出报告。"""
        result = agent.research("人工智能对教育的影响", save_report=False)
        assert result["final_report"] and len(result["final_report"]) > 50

    def test_research_save_report_creates_file(self, agent, tmp_path):
        """save_report=True 时 .md 报告写入磁盘。"""
        agent.config.OUTPUT_DIR = str(tmp_path)
        result = agent.research("测试保存")
        report = result["final_report"]
        assert report
        md_files = [f for f in tmp_path.iterdir() if f.suffix == ".md"]
        assert len(md_files) > 0, f"tmp_path 中没有 .md 文件: {list(tmp_path.iterdir())}"
        assert md_files[0].read_text(encoding="utf-8") == report

    def test_search_failure_propagates_error(self, agent):
        """搜索工具抛出异常时 research() 向上传播。"""
        from unittest.mock import patch
        with patch("MediaEngine.context.MediaContext.execute_search", side_effect=RuntimeError("API unreachable")):
            with pytest.raises(RuntimeError):
                agent.research("测试", save_report=False)

    def test_llm_garbage_still_returns_report(self, agent):
        """LLM 返回非法内容时仍能产出报告，不崩溃。"""
        llm_patch = patch.object(
            agent.llm_client, "stream_invoke_to_string",
            return_value="这是一段无法解析的文本。",
        )
        llm_patch.start()
        try:
            result = agent.research("测试", save_report=False)
            assert result["final_report"] and isinstance(result["final_report"], str) and len(result["final_report"]) > 0
        finally:
            llm_patch.stop()

    def test_progress_callback_receives_events(self, agent):
        """progress_callback 在 research 期间被触发。"""
        events = []
        agent.progress_callback = events.append
        result = agent.research("测试查询")
        assert result["final_report"]
        statuses = [e.get("status") for e in events if "status" in e]
        assert "structure" in statuses
        assert "processing" in statuses
        assert "finalizing" in statuses
