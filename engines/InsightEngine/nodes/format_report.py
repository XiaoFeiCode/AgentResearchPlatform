"""
LangGraph node: format final report from completed paragraphs.
"""

import json

from loguru import logger

from ..state import InsightGraphState
from ..prompts import SYSTEM_PROMPT_REPORT_FORMATTING
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_markdown_tags,
)
from ..context import InsightContext


class FormatReportNode:
    """Format the completed paragraph summaries into a final Markdown report."""

    def __init__(self, ctx):
        self.ctx:InsightContext = ctx

    def __call__(self, state: InsightGraphState) -> dict:
        self._pc({"status": "finalizing", "message": "正在生成最终报告...", "progress_pct": 90})
        logger.info("\n[步骤 3] 生成最终报告...")
        paragraphs = state["paragraphs"]

        report_data = [{
            "title": p["title"],
            "paragraph_latest_state": p.get("research", {}).get("latest_summary", ""),
        } for p in paragraphs]

        try:
            message = json.dumps(report_data, ensure_ascii=False)
            logger.info(f"  开始LLM格式化调用，段落数据大小: {len(message)} 字符")
            raw = self.ctx.llm_client.stream_invoke_to_string(SYSTEM_PROMPT_REPORT_FORMATTING, message)
            logger.info(f"  LLM格式化完成，输出大小: {len(raw)} 字符")
            final_report = self._parse_report(raw)
            logger.info(f"  报告解析完成，最终长度: {len(final_report)} 字符")
        except Exception as e:
            logger.exception(f"LLM格式化失败，使用备用方法: {e}")
            final_report = self._fallback_format(report_data, state.get("report_title", "深度研究报告"))

        return {"final_report": final_report, "is_completed": True}

    # ── Private helpers ──────────────────────────────────────────────

    def _pc(self, data: dict):
        if self.ctx.progress_callback:
            self.ctx.progress_callback(data)

    def _parse_report(self, output: str) -> str:
        cleaned = remove_reasoning_from_output(output)
        cleaned = clean_markdown_tags(cleaned)
        if not cleaned.strip():
            return "# 报告生成失败\n\n无法生成有效的报告内容。"
        if not cleaned.strip().startswith("#"):
            cleaned = "# 深度研究报告\n\n" + cleaned
        return cleaned.strip()

    @staticmethod
    def _fallback_format(paragraphs_data: list, report_title: str = "深度研究报告") -> str:
        """Manual formatting fallback when LLM fails."""
        lines = [f"# {report_title}", "", "---", ""]
        for i, p in enumerate(paragraphs_data, 1):
            content = p.get("paragraph_latest_state", "")
            if content:
                lines.extend([f"## {p.get('title', f'段落 {i}')}", "", content, "", "---", ""])
        if len(paragraphs_data) > 1:
            lines.extend([
                "## 结论", "",
                "本报告通过深度搜索和研究，对相关主题进行了全面分析。"
                "以上各个方面的内容为理解该主题提供了重要参考。", "",
            ])
        return "\n".join(lines)
