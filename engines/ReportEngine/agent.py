"""
ReportEngine entry point — module-level generate_report().

Assembles dependencies, builds the LangGraph, invokes the pipeline,
and returns the generated report.
"""

import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .context import ReportContext, FileCountBaseline
from .graph import build_report_graph
from .llms import LLMClient
from .utils.config import Settings, settings


def generate_report(
    query: str,
    reports: List[Any],
    forum_logs: str = "",
    custom_template: str = "",
    save_report: bool = True,
    stream_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    report_id: Optional[str] = None,
    config: Optional[Settings] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive report (chapter JSON → IR → HTML).

    Args:
        query: Report topic/question.
        reports: Reports from Query/Media/Insight engines.
        forum_logs: Forum discussion text.
        custom_template: Optional custom Markdown template.
        save_report: Persist HTML/IR/state to disk.
        stream_handler: Optional callback for streaming events.
        report_id: Optional task ID for tracking.
        config: Optional config override.

    Returns:
        dict with html_content, report_id, and file paths.
    """
    cfg = config or settings
    rid = report_id or ""
    from uuid import uuid4
    rid = rid.strip() and "".join(c if c.isalnum() or c in ("-_") else "_" for c in rid) or f"report-{uuid4().hex[:8]}"

    # Initialize LLM
    llm_client = LLMClient(
        api_key=cfg.REPORT_ENGINE_API_KEY,
        model_name=cfg.REPORT_ENGINE_MODEL_NAME,
        base_url=cfg.REPORT_ENGINE_BASE_URL,
    )

    # Initialize rescue LLMs
    rescue_clients: List[tuple] = []
    if llm_client:
        rescue_clients.append(("report_engine", llm_client))
    fallback_specs = [
        ("forum_engine", cfg.FORUM_HOST_API_KEY, cfg.FORUM_HOST_MODEL_NAME, cfg.FORUM_HOST_BASE_URL),
        ("insight_engine", cfg.INSIGHT_ENGINE_API_KEY, cfg.INSIGHT_ENGINE_MODEL_NAME, cfg.INSIGHT_ENGINE_BASE_URL),
        ("media_engine", cfg.MEDIA_ENGINE_API_KEY, cfg.MEDIA_ENGINE_MODEL_NAME, cfg.MEDIA_ENGINE_BASE_URL),
    ]
    for label, ak, mn, bu in fallback_specs:
        if ak and mn:
            try:
                rescue_clients.append((label, LLMClient(api_key=ak, model_name=mn, base_url=bu)))
            except Exception as exc:
                logger.warning(f"{label} LLM 初始化失败: {exc}")

    # Ensure directories
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    os.makedirs(cfg.DOCUMENT_IR_OUTPUT_DIR, exist_ok=True)

    # Build context and graph
    ctx = ReportContext(
        llm_client=llm_client,
        config=cfg,
        json_rescue_clients=rescue_clients,
        stream_handler=stream_handler or (lambda evt, pl: None),
    )
    ctx.file_baseline.initialize_baseline({
        'insight': 'data/report/insight',
        'media': 'data/report/media',
        'query': 'data/report/query',
    })

    initial_state = {
        "query": query,
        "reports": reports,
        "forum_logs": forum_logs,
        "custom_template": custom_template,
        "save_report": save_report,
        "report_id": rid,
    }

    try:
        logger.info(f"开始生成报告 {rid}: {query}")
        logger.info(f"输入数据 - 报告数量: {len(reports)}, 论坛日志长度: {len(str(forum_logs))}")

        graph = build_report_graph(ctx)
        result = graph.invoke(initial_state, {"recursion_limit": 50})

        html_content = result.get("html_content", "")
        saved_files = result.get("saved_files", {})
        logger.info(f"报告生成完成: {rid}")

        return {
            "html_content": html_content,
            "report_id": rid,
            **(saved_files or {}),
        }

    except Exception as e:
        logger.exception(f"报告生成失败: {e}")
        raise



def _stringify(value: Any) -> str:
    """Safely convert any value to string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)
    return str(value)
