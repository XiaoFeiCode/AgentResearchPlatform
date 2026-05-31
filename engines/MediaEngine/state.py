"""
MediaEngine LangGraph 状态定义。

TypedDict 用于 LangGraph StateGraph 的节点间数据流转。
"""

from typing import Optional
from typing_extensions import TypedDict


class MediaGraphState(TypedDict, total=False):
    """MediaEngine 的 LangGraph 状态"""

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
