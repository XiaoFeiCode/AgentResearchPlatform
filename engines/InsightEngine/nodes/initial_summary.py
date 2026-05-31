"""
LangGraph node: initial summary — generate paragraph summary from search results.
"""

import json
from copy import deepcopy

from loguru import logger

from app.services.event_bus import publish
from app.services.event_types import EventType
from app.utils.forum_reader import get_latest_host_speech, format_host_speech_for_prompt
from engines.common.structured_output import InitialSummaryOutput
from ..state import InsightGraphState
from ..prompts import SYSTEM_PROMPT_FIRST_SUMMARY
from ..utils import format_search_results_for_prompt
from ..context import InsightContext


class InitialSummaryNode:
    """Generate initial summary for the current paragraph based on search results."""

    def __init__(self, ctx: InsightContext):
        self.ctx = ctx

    def __call__(self, state: InsightGraphState) -> dict:
        idx = state["current_paragraph_index"]
        para = state["paragraphs"][idx]
        research = para.get("research", {})
        current_search = research.get("current_search", {})

        search_query = current_search.get("query", "")
        search_results = current_search.get("results", [])
        search_metadata = current_search.get("metadata", {})
        logger.info("  - 生成初始总结...")

        summary_input = {
            "title": para["title"],
            "content": para["content"],
            "search_query": search_query,
            "search_results": format_search_results_for_prompt(
                search_results, self.ctx.config.MAX_CONTENT_LENGTH,
            ),
        }

        # 将增强管线产出的元信息（情感分析摘要、聚类统计）传给 LLM
        if search_metadata:
            summary_input["search_metadata"] = search_metadata
            if search_metadata.get("sentiment_analysis", {}).get("summary"):
                logger.info(
                    f"  附带情感分析: {search_metadata['sentiment_analysis']['summary']}"
                )
            if search_metadata.get("clustering", {}).get("performed"):
                c = search_metadata["clustering"]
                logger.info(
                    f"  附带聚类信息: {c['original_count']}→{c['sampled_count']} 条"
                )

        try:
            host_speech = get_latest_host_speech()
            if host_speech:
                summary_input["host_speech"] = host_speech
                logger.info(f"  已读取HOST发言，长度: {len(host_speech)}字符")
        except Exception as e:
            logger.exception(f"  读取HOST发言失败: {e}")

        message = json.dumps(summary_input, ensure_ascii=False)
        if "host_speech" in summary_input:
            message = format_host_speech_for_prompt(summary_input["host_speech"]) + "\n" + message

        try:
            out = self.ctx.llm_client.structured_invoke(
                SYSTEM_PROMPT_FIRST_SUMMARY, message, InitialSummaryOutput,
            )
            summary = out.paragraph_latest_state
        except Exception:
            logger.exception("结构化总结输出失败")
            summary = ""

        publish(EventType.SUMMARY_READY, {"source": self.ctx.engine_name, "summary": summary, "type": "initial"})

        updated = deepcopy(state["paragraphs"])
        updated[idx]["research"]["latest_summary"] = summary
        logger.info("  - 初始总结完成")
        return {"paragraphs": updated, "current_reflection_count": 0}
