"""
Shared search execution utility for InitialSearchNode and ReflectionSearchNode.
Extracted from the old graph.py _execute_search_and_convert.
"""

from typing import Any, Dict, Tuple

from loguru import logger
from ..context import InsightContext

def execute_search_and_convert(
    ctx: InsightContext, search_output: dict, search_query: str, search_tool: str
) -> Tuple[list[dict], dict]:
    """LLM 产出搜索参数 → 处理工具选择、参数补全、执行搜索、结果裁切和格式化 →
    返回 (results: list[dict], metadata: dict)，metadata 包含 sentiment_analysis / clustering
    等增强管线产生的元信息，供 summary 节点写入 LLM prompt。
    """
    kwargs: Dict[str, Any] = {}

    if search_tool in ("search_topic_by_date", "search_topic_on_platform"):
        start = search_output.get("start_date")
        end = search_output.get("end_date")
        if start and end:
            if ctx.validate_date_format(start) and ctx.validate_date_format(end):
                kwargs["start_date"] = start
                kwargs["end_date"] = end
            else:
                search_tool = "search_topic_globally"
        elif search_tool == "search_topic_by_date":
            search_tool = "search_topic_globally"

    if search_tool == "search_topic_on_platform":
        platform = search_output.get("platform")
        if platform:
            kwargs["platform"] = platform
        else:
            search_tool = "search_topic_globally"

    if search_tool == "search_hot_content":
        kwargs["time_period"] = search_output.get("time_period", "week")
        kwargs["limit"] = ctx.config.DEFAULT_SEARCH_HOT_CONTENT_LIMIT
    elif search_tool in ("search_topic_globally", "search_topic_by_date"):
        key = "DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE" if search_tool == "search_topic_globally" else "DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE"
        kwargs["limit_per_table"] = getattr(ctx.config, key)
    elif search_tool in ("get_comments_for_topic", "search_topic_on_platform"):
        key = "DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT" if search_tool == "get_comments_for_topic" else "DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT"
        kwargs["limit"] = getattr(ctx.config, key)

    logger.info("  - 执行数据库查询...")
    response = ctx.execute_search(search_tool, search_query, **kwargs)

    results: list[dict] = []
    if response and response.results:
        max_results = ctx.config.MAX_SEARCH_RESULTS_FOR_LLM
        limit = min(len(response.results), max_results) if max_results > 0 else len(response.results)
        for r in response.results[:limit]:
            results.append({
                "title": r.title_or_content, "url": r.url or "",
                "content": r.title_or_content, "score": r.hotness_score,
                "raw_content": r.title_or_content,
                "published_date": r.publish_time.isoformat() if r.publish_time else None,
                "platform": r.platform, "content_type": r.content_type,
                "author": r.author_nickname, "engagement": r.engagement,
            })

    # 提取增强管线元信息（情感分析、聚类），不让它被丢弃
    metadata: dict = {}
    if response and response.parameters:
        if "sentiment_analysis" in response.parameters:
            metadata["sentiment_analysis"] = response.parameters["sentiment_analysis"]
        if "clustering" in response.parameters:
            metadata["clustering"] = response.parameters["clustering"]

    if results:
        msg = f"  - 找到 {len(results)} 个搜索结果"
        for r in results[:5]:
            msg += f"\n    {r['title'][:50]}..."
        logger.info(msg)
    else:
        logger.info("  - 未找到搜索结果")
    return results, metadata
