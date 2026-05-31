"""LangGraph node: initial summary."""

import json
from copy import deepcopy

from loguru import logger

from app.services.event_bus import publish
from app.services.event_types import EventType
from app.utils.forum_reader import get_latest_host_speech, format_host_speech_for_prompt
from engines.common.structured_output import InitialSummaryOutput

from ..state import QueryGraphState
from ..prompts import SYSTEM_PROMPT_FIRST_SUMMARY
from ..utils.text_processing import format_search_results_for_prompt
from ..context import QueryContext


class InitialSummaryNode:
    def __init__(self, ctx: QueryContext):
        self.ctx = ctx

    def __call__(self, state: QueryGraphState) -> dict:
        idx = state["current_paragraph_index"]
        para = state["paragraphs"][idx]
        cs = para.get("research", {}).get("current_search", {})

        logger.info("  - 生成初始总结...")

        payload = {
            "title": para["title"],
            "content": para["content"],
            "search_query": cs.get("query", ""),
            "search_results": format_search_results_for_prompt(
                cs.get("results", []), self.ctx.config.SEARCH_CONTENT_MAX_LENGTH,
            ),
        }

        try:
            host_speech = get_latest_host_speech()
            if host_speech:
                payload["host_speech"] = host_speech
                logger.info(f"  已读取HOST发言，长度: {len(host_speech)}字符")
        except Exception as e:
            logger.exception(f"  读取HOST发言失败: {e}")

        message = json.dumps(payload, ensure_ascii=False)
        if "host_speech" in payload:
            message = format_host_speech_for_prompt(payload["host_speech"]) + "\n" + message

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
