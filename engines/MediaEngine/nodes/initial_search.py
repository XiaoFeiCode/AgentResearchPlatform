"""
LangGraph node: initial search — generate query, execute search, store results.
"""

import json
from copy import deepcopy
from datetime import datetime

from loguru import logger

from engines.common.structured_output import SearchOutput
from ..state import MediaGraphState
from ..prompts import SYSTEM_PROMPT_FIRST_SEARCH
from ._search_utils import execute_search_and_convert


class InitialSearchNode:
    """Generate initial search query for the current paragraph and execute search."""

    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: MediaGraphState) -> dict:
        idx = state["current_paragraph_index"]
        paragraphs = state["paragraphs"]
        para = paragraphs[idx]
        total = len(paragraphs)

        pct = int(20 + (idx + 0.3) / total * 60)
        self.ctx.progress_callback({
            "status": "processing",
            "message": f"处理段落 {idx+1}/{total}: {para['title']}",
            "progress_pct": pct,
            "paragraph_current": idx + 1,
            "paragraph_total": total,
        })

        logger.info(f"\n[步骤 2.{idx + 1}] 处理段落: {para['title']}")
        logger.info("-" * 50)

        search_input = {"title": para["title"], "content": para["content"]}
        logger.info("  - 生成搜索查询...")
        try:
            out = self.ctx.llm_client.structured_invoke(
                SYSTEM_PROMPT_FIRST_SEARCH, json.dumps(search_input, ensure_ascii=False),
                SearchOutput,
            )
        except Exception:
            logger.exception("结构化搜索输出失败，使用默认")
            out = SearchOutput(search_query="相关主题研究", search_tool="comprehensive_search", reasoning="默认搜索")

        search_query = out.search_query
        search_tool = out.search_tool
        logger.info(f"  - 搜索查询: {search_query}, 工具: {search_tool}")

        search_results = execute_search_and_convert(self.ctx, out.model_dump(), search_query, search_tool)

        updated = deepcopy(paragraphs)
        research = updated[idx].setdefault("research", {})
        history = research.setdefault("search_history", [])
        if search_results:
            for r in search_results:
                history.append({
                    "query": search_query, "url": r.get("url", ""),
                    "title": r.get("title", ""), "content": r.get("content", ""),
                    "score": r.get("score"), "paragraph_title": para["title"],
                    "search_tool": search_tool, "has_result": True,
                    "timestamp": datetime.now().isoformat(),
                })
        else:
            history.append({
                "query": search_query, "url": "", "title": "未找到结果",
                "content": "本次搜索未返回结果或调用失败",
                "score": None, "paragraph_title": para["title"],
                "search_tool": search_tool, "has_result": False,
                "timestamp": datetime.now().isoformat(),
            })

        research["current_search"] = {
            "query": search_query, "tool": search_tool, "results": search_results,
        }

        return {"paragraphs": updated}
