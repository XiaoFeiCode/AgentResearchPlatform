"""
InsightEngine LangGraph 状态定义。

将原有 dataclass State 的字段平铺为 TypedDict，
用于 LangGraph StateGraph 的节点间数据流转。
"""

from typing import Optional
from typing_extensions import TypedDict


class InsightGraphState(TypedDict, total=False):
    """InsightEngine 的 LangGraph 状态"""

    # ── 输入 ──
    query: str
    save_report: bool
    max_reflections: int

    # ── 报告结构 ──
    report_title: str
    paragraphs: list[dict]  # 每个元素为 Paragraph.to_dict() 格式

    # ── 循环控制 ──
    current_paragraph_index: int  # 当前正在处理的段落下标
    current_reflection_count: int  # 当前段落已完成的反思次数

    # ── 最终输出 ──
    final_report: str
    is_completed: bool
    error: Optional[str]
