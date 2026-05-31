"""
InsightEngine entry point — 提供模块级别方法： run_research().

The core logic lives in run_research() at module level.
DeepSearchAgent has been removed; graph.py + context.py handle everything.
"""

import os
from typing import Any, Callable, Dict, Optional

from loguru import logger

from .context import InsightContext
from .graph import build_insight_graph
from .llms import LLMClient
from app.config import Settings, settings


# ── Module-level research function ────────────────────────────────────────

def run_research(
    query: str,
    config: Settings,
    llm_client: LLMClient,
    progress_callback: Optional[Callable] = None,
    save_report: bool = True,
) -> Dict[str, Any]:
    """Execute deep research, return dict with final_report and paragraphs."""
    logger.info(f"\n{'=' * 60}\n开始深度研究: {query}\n{'=' * 60}")

    ctx = InsightContext(
        llm_client=llm_client,
        config=config,
        progress_callback=progress_callback,
    )

    # 快速检查本地舆情数据库是否有数据
    try:
        probe = ctx.execute_search("search_hot_content", query, time_period="year", limit=1)
        if not probe.results:
            raise RuntimeError(
                "本地舆情数据库暂无数据，请先运行爬虫采集社交媒体数据。\n"
                "提示: 确认 Docker MySQL 容器已启动，且至少有一张平台表（如 douyin_aweme）包含数据。"
            )
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(f"数据库连通性检查失败: {e}")
        raise RuntimeError("无法连接到本地舆情数据库，请检查数据库配置（DB_HOST/DB_PORT/DB_USER/DB_NAME）。") from e

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    try:
        graph = build_insight_graph(ctx)
        initial_state = {
            "query": query,
            "save_report": save_report,
            "max_reflections": config.MAX_REFLECTIONS,
        }
        result = graph.invoke(initial_state, {"recursion_limit": 100})
        logger.info("深度研究完成！")
        return {
            "final_report": result.get("final_report", ""),
            "report_title": result.get("report_title", ""),
            "is_completed": result.get("is_completed", False),
            "paragraphs": result.get("paragraphs", []),
        }
    except Exception as e:
        logger.exception(f"研究过程中发生错误: {str(e)}")
        raise
