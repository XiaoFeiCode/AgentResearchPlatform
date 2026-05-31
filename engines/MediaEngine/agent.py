"""
MediaEngine entry point — module-level run_research().

MediaEngine has 3 search backends (Bocha, Anspire, Tavily).
The caller injects the right search_agency via config.
"""

import os
from typing import Any, Callable, Dict, Optional

from loguru import logger

from .context import MediaContext
from .graph import build_media_graph
from .llms import LLMClient


def run_research(
    query: str,
    config: Any,
    llm_client: LLMClient,
    search_agency: Any,
    progress_callback: Optional[Callable] = None,
    save_report: bool = True,
) -> Dict[str, Any]:
    """Execute media research, return dict with final_report and paragraphs."""
    logger.info(f"\n{'=' * 60}\n开始媒体研究: {query}\n{'=' * 60}")

    ctx = MediaContext(
        llm_client=llm_client,
        config=config,
        search_agency=search_agency,
        progress_callback=progress_callback,
    )

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    try:
        graph = build_media_graph(ctx)
        initial_state = {
            "query": query,
            "save_report": save_report,
            "max_reflections": config.MAX_REFLECTIONS,
        }
        result = graph.invoke(initial_state, {"recursion_limit": 100})
        logger.info("媒体研究完成！")
        return {
            "final_report": result.get("final_report", ""),
            "report_title": result.get("report_title", ""),
            "is_completed": result.get("is_completed", False),
            "paragraphs": result.get("paragraphs", []),
        }
    except Exception as e:
        logger.exception(f"研究过程中发生错误: {str(e)}")
        raise
