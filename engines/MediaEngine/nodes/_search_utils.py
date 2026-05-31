"""
Shared search execution utility for MediaEngine nodes.
"""

from loguru import logger
from ..context import MediaContext

def execute_search_and_convert(ctx: MediaContext, search_output: dict, search_query: str, search_tool: str) -> list[dict]:
    """Execute search and convert results to standard dict list."""
    kwargs = {}
    if search_tool in ("comprehensive_search", "web_search_only"):
        kwargs["max_results"] = 10

    logger.info("  - 执行网络搜索...")
    response = ctx.execute_search(search_tool, search_query, **kwargs)

    results: list[dict] = []
    if response and response.webpages:
        limit = min(len(response.webpages), 10)
        for r in response.webpages[:limit]:
            results.append({
                "title": r.name, "url": r.url,
                "content": r.snippet, "score": None,
                "raw_content": r.snippet,
                "published_date": r.date_last_crawled,
            })

    if results:
        msg = f"  - 找到 {len(results)} 个搜索结果"
        for r in results[:5]:
            msg += f"\n    {r['title'][:50]}..."
        logger.info(msg)
    else:
        logger.info("  - 未找到搜索结果")

    return results
