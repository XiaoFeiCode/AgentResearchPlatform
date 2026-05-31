"""LangGraph node: format final report."""

import json
from loguru import logger
from ..state import QueryGraphState
from ..prompts import SYSTEM_PROMPT_REPORT_FORMATTING
from ..utils.text_processing import remove_reasoning_from_output, clean_markdown_tags


class FormatReportNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: QueryGraphState) -> dict:
        self._pc({"status": "finalizing", "message": "正在生成最终报告...", "progress_pct": 90})
        logger.info("\n[步骤 3] 生成最终报告...")
        report_data = [{"title": p["title"], "paragraph_latest_state": p.get("research", {}).get("latest_summary", "")} for p in state["paragraphs"]]
        try:
            raw = self.ctx.llm_client.stream_invoke_to_string(SYSTEM_PROMPT_REPORT_FORMATTING, json.dumps(report_data, ensure_ascii=False))
            final_report = self._parse_report(raw)
        except Exception as e:
            logger.error(f"LLM格式化失败，使用备用方法: {e}")
            final_report = self._fallback(report_data, state.get("report_title", "深度研究报告"))
        return {"final_report": final_report, "is_completed": True}

    def _pc(self, data):
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
    def _fallback(data: list, title: str = "深度研究报告") -> str:
        lines = [f"# {title}", "", "---", ""]
        for i, p in enumerate(data, 1):
            c = p.get("paragraph_latest_state", "")
            if c:
                lines.extend([f"## {p.get('title', f'段落 {i}')}", "", c, "", "---", ""])
        if len(data) > 1:
            lines.extend(["## 结论", "", "本报告通过深度搜索和研究，对相关主题进行了全面分析。以上各个方面的内容为理解该主题提供了重要参考。", ""])
        return "\n".join(lines)
