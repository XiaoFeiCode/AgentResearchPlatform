"""LangGraph node: reflection summary."""

import json
from copy import deepcopy

from loguru import logger

from app.services.event_bus import publish
from app.services.event_types import EventType
from app.utils.forum_reader import get_latest_host_speech, format_host_speech_for_prompt
from engines.common.structured_output import ReflectionSummaryOutput

from ..state import QueryGraphState
from ..prompts import SYSTEM_PROMPT_REFLECTION_SUMMARY
from ..utils.text_processing import format_search_results_for_prompt
from ..context import QueryContext


class ReflectionSummaryNode:
    def __init__(self, ctx: QueryContext):
        self.ctx = ctx

    def __call__(self, state: QueryGraphState) -> dict:
        idx = state["current_paragraph_index"]
        para = state["paragraphs"][idx]
        research = para.get("research", {})
        cs = research.get("current_search", {})
        count = state.get("current_reflection_count", 0)
        max_ref = state.get("max_reflections", 2)

        payload = {
            "title": para["title"],
            "content": para["content"],
            "search_query": cs.get("query", ""),
            "search_results": format_search_results_for_prompt(
                cs.get("results", []), self.ctx.config.SEARCH_CONTENT_MAX_LENGTH,
            ),
            "paragraph_latest_state": research.get("latest_summary", ""),
        }

        try:
            host_speech = get_latest_host_speech()
            if host_speech:
                payload["host_speech"] = host_speech
        except Exception:
            pass

        message = json.dumps(payload, ensure_ascii=False)
        if "host_speech" in payload:
            message = format_host_speech_for_prompt(payload["host_speech"]) + "\n" + message

        try:
            out = self.ctx.llm_client.structured_invoke(
                SYSTEM_PROMPT_REFLECTION_SUMMARY, message, ReflectionSummaryOutput,
            )
            summary = out.updated_paragraph_latest_state
        except Exception:
            logger.exception("结构化反思总结输出失败")
            summary = ""

        publish(EventType.SUMMARY_READY, {"source": self.ctx.engine_name, "summary": summary, "type": "reflection"})

        updated = deepcopy(state["paragraphs"])
        updated[idx]["research"]["latest_summary"] = summary
        updated[idx]["research"]["reflection_iteration"] = count + 1
        new_count = count + 1
        logger.info(f"    反思 {new_count} 完成")

        result = {"paragraphs": updated, "current_reflection_count": new_count}

        if new_count >= max_ref:
            updated[idx]["research"]["is_completed"] = True
            total = len(updated)
            pct = int(20 + (idx + 1) / total * 60)
            self.ctx.progress_callback({
                "status": "processing",
                "message": f"段落 {idx+1}/{total} 完成",
                "progress_pct": pct,
                "paragraph_current": idx + 1,
                "paragraph_total": total,
            })
            result["current_paragraph_index"] = idx + 1

        return result
