"""QueryContext — dependency container for QueryEngine graph.

QueryEngine 定位：权威信息核查引擎
- 使用 Bocha 搜索，LLM 提示词侧重官方来源、数据核查、事实验证
- 与 MediaEngine 使用相同的搜索后端，但通过提示词实现角色差异化
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from loguru import logger

from .llms import LLMClient


@dataclass
class QueryContext:
    llm_client: LLMClient
    config: Any
    search_agency: Any
    engine_name: str = "query"
    progress_callback: Optional[Callable] = None

    def execute_search(self, tool_name: str, query: str, **kwargs) -> Any:
        logger.info(f"  → 执行搜索工具: {tool_name}")
        dispatch = {
            "comprehensive_search": lambda: self.search_agency.comprehensive_search(query, kwargs.get("max_results", 10)),
            "web_search_only": lambda: self.search_agency.web_search_only(query, kwargs.get("max_results", 15)),
            "search_for_structured_data": lambda: self.search_agency.search_for_structured_data(query),
            "search_last_24_hours": lambda: self.search_agency.search_last_24_hours(query),
            "search_last_week": lambda: self.search_agency.search_last_week(query),
        }
        fn = dispatch.get(tool_name)
        if fn:
            return fn()
        logger.warning(f"未知搜索工具: {tool_name}，使用默认综合搜索")
        return self.search_agency.comprehensive_search(query)

    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        if not date_str:
            return False
        from datetime import datetime
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
