"""
MediaContext — dependency container for MediaEngine graph.

Holds config, LLM client, search agency, and search dispatch.
LangGraph node classes receive ctx and pull what they need.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from loguru import logger
from langchain_openai import ChatOpenAI
from .llms import LLMClient


@dataclass
class MediaContext:
    """Holds all dependencies needed by MediaEngine's LangGraph nodes."""

    llm_client: ChatOpenAI
    config: Any
    search_agency: Any
    engine_name: str = "media"
    progress_callback: Optional[Callable] = None

    def execute_search(self, tool_name: str, query: str, **kwargs) -> Any:
        """Dispatch to the right search agency method (polymorphic)."""
        logger.info(f"  → 执行搜索工具: {tool_name}")

        dispatch = {
            "comprehensive_search": lambda: self.search_agency.comprehensive_search(
                query, kwargs.get("max_results", 10)),
            "web_search_only": lambda: self._call_agency_method(
                "web_search_only", query, max_results=kwargs.get("max_results", 15)),
            "search_for_structured_data": lambda: self._call_agency_method(
                "search_for_structured_data", query),
            "search_last_24_hours": lambda: self._call_agency_method(
                "search_last_24_hours", query),
            "search_last_week": lambda: self._call_agency_method(
                "search_last_week", query),
        }
        fn = dispatch.get(tool_name)
        if fn:
            return fn()
        logger.info(f"  ⚠️  未知搜索工具: {tool_name}，使用默认综合搜索")
        return self.search_agency.comprehensive_search(query)

    def _call_agency_method(self, method: str, query: str, **kwargs) -> Any:
        """Call a search agency method, falling back to comprehensive_search."""
        fn = getattr(self.search_agency, method, None)
        if fn:
            return fn(query, **kwargs) if kwargs else fn(query)
        logger.info(f"  ⚠️  搜索工具 {self.search_agency.__class__.__name__} 不支持 {method}，使用综合搜索")
        return self.search_agency.comprehensive_search(query)
