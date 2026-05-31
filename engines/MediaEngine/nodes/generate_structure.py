"""
LangGraph node: generate report structure from query.
"""

from loguru import logger

from engines.common.structured_output import ReportStructure
from ..state import MediaGraphState
from ..prompts import SYSTEM_PROMPT_REPORT_STRUCTURE
from ..context import MediaContext


class GenerateStructureNode:
    """Generate the report structure (paragraph list) from the user's query."""

    def __init__(self, ctx: MediaContext):
        self.ctx = ctx

    def __call__(self, state: MediaGraphState) -> dict:
        query = state["query"]
        self.ctx.progress_callback({"status": "structure", "message": "正在生成报告结构...", "progress_pct": 10})
        logger.info(f"\n{'=' * 60}\n[LangGraph] 生成报告结构: {query}")

        try:
            result = self.ctx.llm_client.structured_invoke(
                SYSTEM_PROMPT_REPORT_STRUCTURE, query, ReportStructure,
            )
            structure = result.paragraphs
        except Exception:
            logger.exception("结构化输出失败，使用默认结构")
            structure = []

        if not structure:
            structure = self._default_structure()

        paragraphs = []
        for p in structure:
            if isinstance(p, dict):
                title = p.get("title", "")
                content = p.get("content", "")
            else:
                title = getattr(p, "title", "")
                content = getattr(p, "content", "")

            paragraphs.append({
                "title": title, "content": content,
                "research": {"search_history": [], "latest_summary": "", "is_completed": False, "reflection_iteration": 0},
            })

        msg = f"报告结构已生成，共 {len(paragraphs)} 个段落:"
        for i, p in enumerate(paragraphs, 1):
            msg += f"\n  {i}. {p['title']}"
        logger.info(msg)

        return {
            "report_title": f"关于'{query}'的深度研究报告",
            "paragraphs": paragraphs,
            "current_paragraph_index": 0,
            "current_reflection_count": 0,
        }

    @staticmethod
    def _default_structure() -> list:
        return [
            {"title": "研究概述", "content": "对查询主题进行总体概述和分析"},
            {"title": "深度分析", "content": "深入分析查询主题的各个方面"},
        ]
