"""Shared search execution utility for QueryEngine nodes."""

from loguru import logger

from ..utils.source_classifier import (
    build_authority_queries,
    classify_source,
    source_rank,
)
from ..context import QueryContext


def execute_search_and_convert(ctx: QueryContext, search_output: dict, search_query: str, search_tool: str) -> list[dict]:
    kwargs = {}
    if search_tool == "search_last_24_hours":
        kwargs["max_results"] = 10
    elif search_tool == "search_last_week":
        kwargs["max_results"] = 10

    logger.info("  - 执行权威信息搜索...")
    queries = build_authority_queries(search_query)
    seen_urls: set[str] = set()

    results: list[dict] = []
    for query in queries:
        response = ctx.execute_search(search_tool, query, **kwargs)
        if not response or not response.webpages:
            continue

        for w in response.webpages:
            url = w.url or ""
            dedupe_key = url or f"{w.name}:{w.snippet}"
            if dedupe_key in seen_urls:
                continue
            seen_urls.add(dedupe_key)

            rating = classify_source(url)
            results.append({
                "title": w.name, "url": w.url, "content": w.snippet,
                "score": None, "raw_content": w.snippet,
                "published_date": w.date_last_crawled,
                "search_query_used": query,
                **rating,
            })

    results.sort(key=lambda r: (source_rank(r.get("source_type", "")), -(r.get("score") or 0)))
    results = results[:15]

    if results:
        msg = f"  - 找到 {len(results)} 个搜索结果"
        for r in results[:5]:
            msg += f"\n    [{r.get('source_label')}] {r['title'][:50]}..."
        logger.info(msg)
    else:
        logger.info("  - 未找到搜索结果")
    return results
