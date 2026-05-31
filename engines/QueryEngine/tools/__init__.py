"""
工具调用模块
QueryEngine 与 MediaEngine 共用 Bocha 搜索后端，
通过 LLM 提示词实现角色差异化（权威核查 vs 舆情分析）。
"""

from engines.MediaEngine.tools.search import (
    BochaMultimodalSearch,
    WebpageResult,
    BochaResponse,
)

# 保留 Tavily 相关导出以备未来切换
from .search import (
    TavilyNewsAgency,
    SearchResult,
    TavilyResponse,
    ImageResult,
    print_response_summary,
)

__all__ = [
    "BochaMultimodalSearch",
    "WebpageResult",
    "BochaResponse",
    "TavilyNewsAgency",
    "SearchResult",
    "TavilyResponse",
    "ImageResult",
    "print_response_summary",
]
