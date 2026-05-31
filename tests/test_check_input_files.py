"""
Test check_input_files and generate_report — without requiring all engines.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

_proj_root = Path(__file__).resolve().parent.parent
for _p in [str(_proj_root), str(_proj_root / "engines")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_CUSTOM_TEMPLATE = "# 第一章：市场概况\n- 市场整体表现\n# 第二章：趋势分析\n- 发展趋势\n"


def _make_chapter(cid: str, title: str) -> dict:
    return {"chapter_id": cid, "title": title, "slug": f"chapter-{cid}", "blocks": [
        {"type": "heading", "level": 1, "text": title, "anchor": f"sec-{cid}-1"},
        {"type": "paragraph", "inlines": [{"text": f"这是{title}的正文内容。"}]},
    ]}


def test_check_input_files():
    """check_engines_ready returns ready=True when files exist."""
    from app.services.report_service import check_engines_ready
    result = check_engines_ready()
    assert result["ready"] is True, f"ready=False, missing: {result.get('missing_files')}"
    assert len(result.get("latest_files", {})) >= 1
    print(f"[PASS] check_input_files: ready=True, files={list(result.get('latest_files', {}).keys())}")


def test_generate_report_without_insight():
    """2 reports (media + query, no insight) still generates HTML."""
    from ReportEngine.agent import generate_report
    from ReportEngine.utils.config import Settings

    config = Settings(
        REPORT_ENGINE_API_KEY="sk-fake-key", REPORT_ENGINE_MODEL_NAME="test-model",
        REPORT_ENGINE_BASE_URL="https://test.api.com",
        OUTPUT_DIR="/tmp/test_report_reports", CHAPTER_OUTPUT_DIR="/tmp/test_report_reports/chapters",
        DOCUMENT_IR_OUTPUT_DIR="/tmp/test_report_reports/ir",
    )
    chapter_responses = {"S1": _make_chapter("S1", "市场概况"), "S2": _make_chapter("S2", "趋势分析")}
    fake_chapter = lambda section, ctx, run_dir, **kw: chapter_responses.get(getattr(section, "chapter_id", None), _make_chapter("S0", "未知"))

    with patch("ReportEngine.nodes.design_layout.DesignLayoutNode.run", return_value={"title": "测试报告", "tocTitle": "目录", "hero": {}}):
        with patch("ReportEngine.nodes.plan_budget.PlanBudgetNode.run", return_value={"totalWords": 1000, "chapters": [{"chapterId": "S1", "targetWords": 500}, {"chapterId": "S2", "targetWords": 500}]}):
            with patch("ReportEngine.nodes.generate_chapters.GenerateChaptersNode.run", side_effect=fake_chapter):
                with patch("ReportEngine.nodes.select_template.SelectTemplateNode.run", return_value={"template_name": "test", "template_content": _CUSTOM_TEMPLATE, "selection_reason": "test"}):
                    reports = ["# QueryEngine 报告", "# MediaEngine 报告"]
                    result = generate_report(query="市场分析", reports=reports, forum_logs="论坛日志", custom_template=_CUSTOM_TEMPLATE, save_report=False, config=config)

    html = result.get("html_content", "")
    assert isinstance(html, str) and len(html) > 100, f"HTML 不足: {len(html)}"
    assert "<html" in html.lower() or "<!doctype" in html.lower()
    print(f"[PASS] generate_report without insight: HTML {len(html)} chars")


if __name__ == "__main__":
    test_check_input_files()
    test_generate_report_without_insight()
    print("\n✅ 全部通过！")
