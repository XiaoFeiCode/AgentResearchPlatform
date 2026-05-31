"""
端到端测试：ReportEngine

Mock 掉调用 LLM 的节点方法（design_layout / plan_budget /
generate_chapters），验证 generate_report() 的管道编排行为：
输入 query + reports → 输出 HTML。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── 路径 ─────────────────────────────────────────────────────
_proj_root = Path(__file__).resolve().parent.parent
for _p in [str(_proj_root), str(_proj_root / "engines")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── 模板 ──────────────────────────────────────────────────────
from ReportEngine.utils.config import Settings

_CUSTOM_TEMPLATE = """# 第一章：市场概况
- 市场整体表现
- 主要数据指标

# 第二章：趋势分析
- 发展趋势
- 前景展望
"""

_MOCK_REPORTS = [
    "# QueryEngine 报告\n查询引擎分析结果。",
    "# MediaEngine 报告\n媒体引擎分析结果。",
    "# InsightEngine 报告\n洞察引擎分析结果。",
]

# ── 节点 mock 返回值 ─────────────────────────────────────────

def _make_layout():
    """返回符合 document_layout 输出契约的 dict。"""
    return {
        "title": "舆情分析报告",
        "subtitle": "综合数据洞察",
        "tagline": "基于多引擎数据的深度分析",
        "tocTitle": "目录",
        "hero": {
            "summary": "本报告综合分析了市场概况和趋势。",
            "highlights": ["市场整体表现良好", "新兴趋势值得关注"],
            "kpis": [{"label": "声量", "value": "125万", "tone": "up"}],
            "actions": ["持续关注市场动态"],
        },
        "tocPlan": [
            {
                "chapterId": "S1", "anchor": "chapter-1",
                "display": "一、市场概况",
                "description": "分析市场整体表现和数据指标",
            },
            {
                "chapterId": "S2", "anchor": "chapter-2",
                "display": "二、趋势分析",
                "description": "分析发展趋势和前景展望",
            },
        ],
        "layoutNotes": ["采用标准报告布局"],
    }


def _make_word_budget():
    """返回符合 word_budget 输出契约的 dict。"""
    return {
        "totalWords": 2000,
        "tolerance": 200,
        "chapters": [
            {
                "chapterId": "S1", "title": "市场概况", "targetWords": 1000,
                "sections": [
                    {"title": "市场整体表现", "anchor": "sec-1-1", "targetWords": 500, "minWords": 200, "maxWords": 600},
                    {"title": "主要数据指标", "anchor": "sec-1-2", "targetWords": 500, "minWords": 200, "maxWords": 600},
                ],
            },
            {
                "chapterId": "S2", "title": "趋势分析", "targetWords": 1000,
                "sections": [
                    {"title": "发展趋势", "anchor": "sec-2-1", "targetWords": 500, "minWords": 200, "maxWords": 600},
                    {"title": "前景展望", "anchor": "sec-2-2", "targetWords": 500, "minWords": 200, "maxWords": 600},
                ],
            },
        ],
    }


def _make_chapter(chapter_id: str, title: str) -> dict:
    """返回符合 chapter JSON 输出契约的 dict。"""
    return {
        "chapter_id": chapter_id,
        "title": title,
        "slug": f"chapter-{chapter_id}",
        "content": [
            {"type": "heading", "anchor": f"sec-{chapter_id}-1", "text": title},
            {"type": "paragraph", "inlines": [{"text": f"这是{title}的正文内容。"}]},
        ],
    }


# ── Fixture ───────────────────────────────────────────────────

@pytest.fixture
def agent():
    """Mock business-logic nodes and call generate_report() directly."""
    from unittest.mock import patch
    from ReportEngine.agent import generate_report
    from ReportEngine.utils.config import Settings

    config = Settings(
        REPORT_ENGINE_API_KEY="sk-fake-key",
        REPORT_ENGINE_MODEL_NAME="test-model",
        REPORT_ENGINE_BASE_URL="https://test.api.com",
        OUTPUT_DIR="/tmp/test_report_reports",
        CHAPTER_OUTPUT_DIR="/tmp/test_report_reports/chapters",
        DOCUMENT_IR_OUTPUT_DIR="/tmp/test_report_reports/ir",
    )

    chapter_responses = {
        "S1": _make_chapter("S1", "市场概况"),
        "S2": _make_chapter("S2", "趋势分析"),
    }

    def fake_chapter(section, context, run_dir, **kwargs):
        cid = getattr(section, "chapter_id", None)
        if cid and cid in chapter_responses:
            return chapter_responses[cid]
        return _make_chapter(cid or "S0", getattr(section, "title", "未知章节"))

    patches = [
        patch("ReportEngine.nodes.design_layout.DesignLayoutNode.run", return_value=_make_layout()),
        patch("ReportEngine.nodes.plan_budget.PlanBudgetNode.run", return_value=_make_word_budget()),
        patch("ReportEngine.nodes.generate_chapters.GenerateChaptersNode.run", side_effect=fake_chapter),
        patch("ReportEngine.nodes.select_template.SelectTemplateNode.run", return_value={
            "template_name": "test_template",
            "template_content": _CUSTOM_TEMPLATE,
            "selection_reason": "test",
        }),
    ]
    for p in patches:
        p.start()

    def _run(**kwargs):
        defaults = dict(query="测试", reports=[], forum_logs="", custom_template="", save_report=False, report_id="test-report", config=config)
        defaults.update(kwargs)
        return generate_report(**defaults)

    yield _run

    for p in patches:
        p.stop()


class TestReportEngineBehavior:
    """ReportEngine 行为级端到端测试，只验证外部契约。"""

    def test_generate_report_returns_html(self, agent):
        result = agent(query="市场分析", reports=_MOCK_REPORTS, forum_logs="论坛讨论内容", custom_template="# 模板\n- 内容", save_report=False)
        assert isinstance(result, dict)
        html = result.get("html_content", "")
        assert html and isinstance(html, str) and len(html) > 100
        assert "<html" in html.lower() or "<!doctype" in html.lower()

    def test_generate_report_with_chinese_query(self, agent):
        result = agent(query="人工智能行业舆情分析", reports=_MOCK_REPORTS, custom_template="# 模板\n- 内容", save_report=False)
        assert result.get("html_content") and len(result["html_content"]) > 100

    def test_generate_report_save_creates_file(self, agent, tmp_path):
        result = agent(query="测试保存", reports=_MOCK_REPORTS, save_report=True, config=Settings(
            REPORT_ENGINE_API_KEY="sk-fake-key", REPORT_ENGINE_MODEL_NAME="test-model",
            REPORT_ENGINE_BASE_URL="https://test.api.com",
            OUTPUT_DIR=str(tmp_path), CHAPTER_OUTPUT_DIR=str(tmp_path / "chapters"),
            DOCUMENT_IR_OUTPUT_DIR=str(tmp_path / "ir"),
        ))
        html_content = result.get("html_content", "")
        assert html_content
        html_files = [f for f in tmp_path.rglob("*.html")]
        assert len(html_files) > 0
        assert html_files[0].read_text(encoding="utf-8") == html_content

    def test_empty_reports_still_generates_html(self, agent):
        result = agent(query="测试", reports=[], custom_template="# 模板\n- 内容", save_report=False)
        assert result.get("html_content") and len(result["html_content"]) > 50

    def test_empty_forum_logs_still_generates_html(self, agent):
        result = agent(query="测试", reports=_MOCK_REPORTS, forum_logs="", custom_template="# 模板\n- 内容", save_report=False)
        assert result.get("html_content") and len(result["html_content"]) > 50

    def test_custom_template_does_not_crash(self, agent):
        """custom_template 参数正常传递，不崩溃。"""
        result = agent(query="测试", reports=_MOCK_REPORTS, custom_template="# 标题A\n- 内容A", save_report=False)
        assert result.get("html_content") and len(result["html_content"]) > 50
