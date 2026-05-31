"""QueryEngine entry point — module-level run_research()."""

import os
from typing import Any, Callable, Dict, Optional

from .context import QueryContext
from .graph import build_query_graph
from .llms import LLMClient
from loguru import logger


def run_research(
    query: str,
    config: Any,
    llm_client: LLMClient,
    search_agency: Any,
    progress_callback: Optional[Callable] = None,
    save_report: bool = True,
) -> Dict[str, Any]:
    logger.info(f"\n{'=' * 60}\n开始深度研究: {query}\n{'=' * 60}")
    ctx = QueryContext(llm_client=llm_client, config=config, search_agency=search_agency, progress_callback=progress_callback)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    try:
        result = build_query_graph(ctx).invoke({"query": query, "save_report": save_report, "max_reflections": config.MAX_REFLECTIONS}, {"recursion_limit": 100})
        logger.info("深度研究完成！")
        return {"final_report": result.get("final_report", ""), "report_title": result.get("report_title", ""), "is_completed": result.get("is_completed", False), "paragraphs": result.get("paragraphs", [])}
    except Exception as e:
        logger.exception(f"研究过程中发生错误: {str(e)}")
        raise
