"""QueryEngine LangGraph 状态定义。"""
from typing import Optional
from typing_extensions import TypedDict


class QueryGraphState(TypedDict, total=False):
    query: str
    save_report: bool
    max_reflections: int
    report_title: str
    paragraphs: list[dict]
    current_paragraph_index: int
    current_reflection_count: int
    final_report: str
    is_completed: bool
    error: Optional[str]
