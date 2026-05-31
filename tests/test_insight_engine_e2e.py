"""
端到端测试：InsightEngine 重构（死代码删除 + progress_callback + 循环导入修复）

使用 mock 替换所有外部依赖（LLM API、数据库、关键词优化器），
验证 research() 在 LangGraph 流程中完整走通。
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# ── 先把项目根路径和 engines/ 加入 sys.path ─────────────────
_proj_root = Path(__file__).resolve().parent.parent
for _p in [str(_proj_root), str(_proj_root / "engines")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── 辅助函数：构造假的 DBResponse ────────────────────────────
def _fake_db_response(results_count: int = 3) -> "DBResponse":
    from InsightEngine.tools.search import DBResponse, QueryResult
    results = []
    for i in range(results_count):
        results.append(QueryResult(
            platform="weibo",
            content_type="post",
            title_or_content=f"测试搜索结果第{i+1}条",
            author_nickname=f"作者{i+1}",
            url=f"https://weibo.com/test/{i}",
            publish_time=datetime.now(),
            engagement={"like": 10, "comment": 5},
            hotness_score=0.8 - i * 0.1,
            source_table="weibo_note",
        ))
    return DBResponse(
        tool_name="search_topic_globally",
        parameters={"query": "test"},
        results=results,
        results_count=len(results),
    )


# ── LLM mock 响应（按调用顺序） ─────────────────────────────
# 流程：generate_structure → (2 个段落各: initial_search → initial_summary
#       → reflection_search → reflection_summary) → format_report
# MAX_REFLECTIONS=2, 以 search_service 的设置为准
# 总调用数：1(generate) + 2*(1+1+2+2)(段落) + 1(format) = 14
_MOCK_LLM_RESPONSES = [
    # 1. ReportStructureNode
    json.dumps([
        {"title": "市场概况", "content": "分析市场整体表现"},
        {"title": "竞争格局", "content": "分析主要竞争对手"},
    ], ensure_ascii=False),
    # 2. FirstSearchNode (段落1)
    json.dumps({"search_query": "市场概况 数据", "search_tool": "search_topic_globally", "reasoning": "需要获取市场数据"}, ensure_ascii=False),
    # 3. FirstSummaryNode (段落1)
    json.dumps({"paragraph_latest_state": "## 市场概况\n2025年市场整体表现良好。"}, ensure_ascii=False),
    # 4. ReflectionNode (段落1 - 第1轮)
    json.dumps({"search_query": "市场 最新动态", "search_tool": "search_hot_content", "reasoning": "需要补充最新动态"}, ensure_ascii=False),
    # 5. ReflectionSummaryNode (段落1 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 市场概况（更新）\n2025年市场整体表现良好，最新数据显示增长加速。"}, ensure_ascii=False),
    # 6. ReflectionNode (段落1 - 第2轮)
    json.dumps({"search_query": "市场 风险因素", "search_tool": "search_hot_content", "reasoning": "需要检查风险"}, ensure_ascii=False),
    # 7. ReflectionSummaryNode (段落1 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 市场概况（最终）\n2025年市场整体表现良好，增长加速，需关注政策风险。"}, ensure_ascii=False),
    # 8. FirstSearchNode (段落2)
    json.dumps({"search_query": "竞争格局 分析", "search_tool": "search_topic_globally", "reasoning": "需要获取竞争数据"}, ensure_ascii=False),
    # 9. FirstSummaryNode (段落2)
    json.dumps({"paragraph_latest_state": "## 竞争格局\n主要竞争对手包括A、B、C三家。"}, ensure_ascii=False),
    # 10. ReflectionNode (段落2 - 第1轮)
    json.dumps({"search_query": "竞争对手 动态", "search_tool": "search_hot_content", "reasoning": "需要补充竞品动态"}, ensure_ascii=False),
    # 11. ReflectionSummaryNode (段落2 - 第1轮)
    json.dumps({"updated_paragraph_latest_state": "## 竞争格局（更新）\nA公司推出新产品，B公司市场份额下降。"}, ensure_ascii=False),
    # 12. ReflectionNode (段落2 - 第2轮)
    json.dumps({"search_query": "竞争 趋势预测", "search_tool": "search_hot_content", "reasoning": "需要分析趋势"}, ensure_ascii=False),
    # 13. ReflectionSummaryNode (段落2 - 第2轮)
    json.dumps({"updated_paragraph_latest_state": "## 竞争格局（最终）\nA公司领先，B公司下滑，C公司崛起。"}, ensure_ascii=False),
    # 14. ReportFormattingNode
    "# 深度研究报告\n\n## 市场概况\n2025年市场整体表现良好。\n\n## 竞争格局\n主要竞争对手包括A、B、C三家。",
]


class TestLazyKeywordOptimizer:
    """独立测试类：keyword_optimizer 懒加载机制（不需 agent 实例）。"""

    def test_module_level_variable_is_none(self):
        """验证模块级 keyword_optimizer 初始为 None，不再在 import 时抛 ValueError。"""
        import importlib
        ko_mod = importlib.import_module("InsightEngine.tools.keyword_optimizer")
        assert ko_mod.keyword_optimizer is None

    def test_get_keyword_optimizer_function_exists(self):
        """验证 get_keyword_optimizer 函数可调用（实际实例化需真实 API key）。"""
        import importlib
        ko_mod = importlib.import_module("InsightEngine.tools.keyword_optimizer")
        assert callable(ko_mod.get_keyword_optimizer)


class TestInsightEngineE2E:
    """InsightEngine 端到端测试（全 mock 外部依赖）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前准备 mock 环境和 agent 实例。"""
        # ── 1. patch LLM 调用 ──
        self._llm_responses = list(_MOCK_LLM_RESPONSES)  # 可消费的副本
        self._llm_call_count = 0

        def _fake_stream_invoke(system_prompt: str, message: str) -> str:
            """按顺序返回预定义的 LLM 响应。"""
            self._llm_call_count += 1
            idx = self._llm_call_count - 1
            if idx < len(self._llm_responses):
                return self._llm_responses[idx]
            return "{}"

        self._llm_patch = patch(
            "InsightEngine.llms.base.LLMClient.stream_invoke_to_string",
            side_effect=_fake_stream_invoke,
        )
        self._llm_patch.start()

        # ── 2. patch 数据库搜索工具（移至 InsightContext） ──
        self._search_patch = patch(
            "InsightEngine.context.InsightContext.execute_search",
            return_value=_fake_db_response(3),
        )
        self._search_patch.start()

        # ── 3. patch 关键词优化器（懒加载路径） ──
        self._ko_mock = MagicMock()
        self._ko_mock.optimize_keywords.return_value = MagicMock(
            optimized_keywords=["测试关键词"],
            reasoning="测试",
        )
        self._ko_patch = patch(
            "InsightEngine.context.get_keyword_optimizer",
            return_value=self._ko_mock,
        )
        self._ko_patch.start()

        # ── 4. 禁用情感分析 ──
        self._sa_patch = patch(
            "InsightEngine.tools.sentiment_analyzer.multilingual_sentiment_analyzer.is_disabled",
            new_callable=PropertyMock,
            return_value=True,
        )
        self._sa_patch.start()

        # ── 5. 禁用聚类 ──
        self._cluster_patch = patch(
            "InsightEngine.context.ENABLE_CLUSTERING",
            False,
        )
        self._cluster_patch.start()

        # ── 6. 创建 run_research 依赖 ──
        self.progress_callback = None
        from InsightEngine.agent import run_research
        from InsightEngine.llms import LLMClient
        from app.config import Settings

        self.config = Settings(
            INSIGHT_ENGINE_API_KEY="sk-test-fake-key",
            INSIGHT_ENGINE_MODEL_NAME="test-model",
            INSIGHT_ENGINE_BASE_URL="https://test.api.com",
            DB_HOST="localhost", DB_USER="test",
            DB_PASSWORD="test", DB_NAME="test",
            DB_PORT=3306, DB_CHARSET="utf8mb4", DB_DIALECT="mysql",
            MAX_REFLECTIONS=2, MAX_CONTENT_LENGTH=500000,
            OUTPUT_DIR="/tmp/test_insight_reports",
        )
        self.llm_client = LLMClient(
            api_key=self.config.INSIGHT_ENGINE_API_KEY,
            model_name=self.config.INSIGHT_ENGINE_MODEL_NAME,
            base_url=self.config.INSIGHT_ENGINE_BASE_URL,
        )

        def _research(query, save_report=True):
            return run_research(query, self.config, self.llm_client,
                                self.progress_callback, save_report)

        self._research = _research

        yield

        # ── 清理 ──
        self._llm_patch.stop()
        self._search_patch.stop()
        self._ko_patch.stop()
        self._sa_patch.stop()
        self._cluster_patch.stop()

    # ── 测试用例 ──────────────────────────────────────────────

    def test_import_chain(self):
        """验证完整的导入链正常。"""
        from InsightEngine import run_research
        from InsightEngine.graph import build_insight_graph, _should_continue_reflection, _has_more_paragraphs
        from InsightEngine.state import InsightGraphState
        from InsightEngine.tools import get_keyword_optimizer
        assert run_research is not None
        assert build_insight_graph is not None
        assert InsightGraphState is not None
        assert _should_continue_reflection is not None
        assert _has_more_paragraphs is not None

    def test_progress_callback_attribute(self):
        """验证 progress_callback 参数可接受 None。"""
        result = self._research("测试查询", save_report=False)
        assert result["final_report"]

    def test_progress_callback_triggered(self):
        """验证 research() 执行过程中 progress_callback 被按阶段触发。"""
        events = []

        def _cb(data: dict):
            events.append(data)

        self.progress_callback = _cb
        result = self._research("测试查询")
        report = result["final_report"]

        # 验证报告被生成
        assert report
        assert "# 深度研究报告" in report

        # 验证回调事件
        statuses = [e.get("status") for e in events]
        assert "structure" in statuses, f"缺少 structure 事件: {statuses}"
        assert "processing" in statuses, f"缺少 processing 事件: {statuses}"
        assert "finalizing" in statuses, f"缺少 finalizing 事件: {statuses}"
        assert "saving" in statuses, f"缺少 saving 事件: {statuses}"

        # 验证 progress_pct 递增
        pcts = [e.get("progress_pct", 0) for e in events if "progress_pct" in e]
        assert pcts == sorted(pcts), f"progress_pct 未递增: {pcts}"

        # 验证段落进度
        processing = [e for e in events if e.get("status") == "processing"]
        assert len(processing) >= 4, f"processing 事件不足: {len(processing)}"

    def test_research_flow(self):
        """验证完整的 research() 流程产出正确结果。"""
        result = self._research("测试查询", save_report=False)
        report = result["final_report"]

        # 返回非空报告
        assert report
        assert isinstance(report, str)
        assert len(report) > 50

        # 确认 LLM 被调用了足够次数
        assert self._llm_call_count >= 10, f"LLM 调用不足: {self._llm_call_count}"

    def test_state_sync(self):
        """验证 research() 返回结果包含完整段落和搜索历史（供 citations 提取）。"""
        result = self._research("测试查询")
        report = result["final_report"]
        paragraphs = result.get("paragraphs", [])

        assert report
        assert result.get("is_completed") is True
        assert len(paragraphs) == 2

        for p_dict in paragraphs:
            assert p_dict.get("title")
            research = p_dict.get("research", {})
            assert research.get("latest_summary")
            assert research.get("is_completed")
            assert len(research.get("search_history", [])) > 0
            for search in research["search_history"]:
                assert search.get("query")

    def test_deep_search_agent_removed(self):
        """验证 DeepSearchAgent 类已从 InsightEngine 中移除。"""
        import importlib
        mod = importlib.import_module("InsightEngine")
        assert not hasattr(mod, "DeepSearchAgent")
        assert hasattr(mod, "run_research")

    def test_graph_uses_node_classes(self):
        """验证 graph.py 使用新 node classes 构建图。"""
        from InsightEngine.graph import build_insight_graph
        import inspect
        source = inspect.getsource(build_insight_graph)
        assert "GenerateStructureNode(ctx)" in source
        assert "InitialSearchNode(ctx)" in source
        assert "InitialSummaryNode(ctx)" in source
        assert "ReflectionSearchNode(ctx)" in source
        assert "ReflectionSummaryNode(ctx)" in source
        assert "FormatReportNode(ctx)" in source
        assert "SaveReportNode(ctx)" in source

    def test_callbacks_no_error_without_callback(self):
        """验证未传入 progress_callback 时不会报错。"""
        assert self.progress_callback is None
        result = self._research("无回调测试", save_report=False)
        assert result["final_report"]

    # test_lazy_keyword_optimizer 已移到 TestLazyKeywordOptimizer


# ── 条件边函数测试（纯函数，零依赖） ──────────────────────────


class TestConditionalEdgeFunctions:
    """直接测试 graph.py 中的条件边函数，不依赖任何 mock。"""

    def test_should_continue_reflection_before_max(self):
        """current_reflection_count < max_reflections 时返回 reflect_again。"""
        from InsightEngine.graph import _should_continue_reflection
        from InsightEngine.state import InsightGraphState

        s = InsightGraphState(current_reflection_count=0, max_reflections=3)
        assert _should_continue_reflection(s) == "reflect_again"

        s["current_reflection_count"] = 2
        assert _should_continue_reflection(s) == "reflect_again"

    def test_should_continue_reflection_at_max(self):
        """current_reflection_count >= max_reflections 时返回 next_paragraph。"""
        from InsightEngine.graph import _should_continue_reflection
        from InsightEngine.state import InsightGraphState

        s = InsightGraphState(current_reflection_count=3, max_reflections=3)
        assert _should_continue_reflection(s) == "next_paragraph"

        s["current_reflection_count"] = 5
        assert _should_continue_reflection(s) == "next_paragraph"

    def test_has_more_paragraphs_before_end(self):
        """current_paragraph_index < len(paragraphs) 时返回 process_next。"""
        from InsightEngine.graph import _has_more_paragraphs
        from InsightEngine.state import InsightGraphState

        s = InsightGraphState(current_paragraph_index=0, paragraphs=[{"title": "a"}, {"title": "b"}])
        assert _has_more_paragraphs(s) == "process_next"

        s["current_paragraph_index"] = 1
        assert _has_more_paragraphs(s) == "process_next"

    def test_has_more_paragraphs_at_end(self):
        """current_paragraph_index >= len(paragraphs) 时返回 all_done。"""
        from InsightEngine.graph import _has_more_paragraphs
        from InsightEngine.state import InsightGraphState

        s = InsightGraphState(current_paragraph_index=2, paragraphs=[{"title": "a"}, {"title": "b"}])
        assert _has_more_paragraphs(s) == "all_done"

    def test_has_more_paragraphs_empty(self):
        """段落列表为空时直接返回 all_done。"""
        from InsightEngine.graph import _has_more_paragraphs
        from InsightEngine.state import InsightGraphState

        s = InsightGraphState(current_paragraph_index=0, paragraphs=[])
        assert _has_more_paragraphs(s) == "all_done"


# ── 行为级端到端测试（黑盒，不依赖内部实现细节） ──────────────

_AGENT_CONFIG = dict(
    INSIGHT_ENGINE_API_KEY="sk-test-fake-key",
    INSIGHT_ENGINE_MODEL_NAME="test-model",
    INSIGHT_ENGINE_BASE_URL="https://test.api.com",
    DB_HOST="localhost", DB_USER="test", DB_PASSWORD="test",
    DB_NAME="test", DB_PORT=3306, DB_CHARSET="utf8mb4", DB_DIALECT="mysql",
    MAX_REFLECTIONS=2,
    MAX_CONTENT_LENGTH=500000,
)


@pytest.fixture
def agent():
    """创建 mock 好外部依赖的 runner。每个测试独享一份。"""
    llm_responses = list(_MOCK_LLM_RESPONSES)
    call_count = 0

    def _fake_llm(system_prompt: str, message: str) -> str:
        nonlocal call_count
        call_count += 1
        idx = call_count - 1
        return llm_responses[idx] if idx < len(llm_responses) else "{}"

    patches = [
        patch("InsightEngine.llms.base.LLMClient.stream_invoke_to_string", side_effect=_fake_llm),
        patch("InsightEngine.context.InsightContext.execute_search", return_value=_fake_db_response(3)),
        patch("InsightEngine.context.get_keyword_optimizer", return_value=MagicMock(
            optimize_keywords=MagicMock(return_value=MagicMock(optimized_keywords=["测试关键词"], reasoning="测试")),
        )),
        patch("InsightEngine.tools.sentiment_analyzer.multilingual_sentiment_analyzer.is_disabled",
              new_callable=PropertyMock, return_value=True),
        patch("InsightEngine.context.ENABLE_CLUSTERING", False),
    ]
    for p in patches:
        p.start()

    from InsightEngine.agent import run_research
    from InsightEngine.llms import LLMClient
    from app.config import Settings

    config = Settings(OUTPUT_DIR="/tmp/test_insight_reports", **_AGENT_CONFIG)
    llm_client = LLMClient(
        api_key=config.INSIGHT_ENGINE_API_KEY,
        model_name=config.INSIGHT_ENGINE_MODEL_NAME,
        base_url=config.INSIGHT_ENGINE_BASE_URL,
    )

    runner = SimpleNamespace()
    runner.config = config
    runner.llm_client = llm_client
    runner.progress_callback = None
    runner.research = lambda query, save_report=True: run_research(
        query, config, llm_client, runner.progress_callback, save_report,
    )

    yield runner

    for p in patches:
        p.stop()


class TestInsightEngineBehavior:
    """InsightEngine 行为级端到端测试，只验证外部契约。"""

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

    def test_db_failure_propagates_error(self, agent):
        """数据库查询失败时 research() 抛出异常。"""
        with patch(
            "InsightEngine.context.InsightContext.execute_search",
            side_effect=RuntimeError("DB unreachable"),
        ):
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
        # 验证关键阶段事件被触发
        assert "structure" in statuses
        assert "processing" in statuses
        assert "finalizing" in statuses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
