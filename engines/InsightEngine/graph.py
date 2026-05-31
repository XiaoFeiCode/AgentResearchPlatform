"""
InsightEngine LangGraph 图定义。

build_insight_graph(ctx) 构建 StateGraph，
将节点类（__call__(state) -> dict）注册到图中。
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from .context import InsightContext
from .state import InsightGraphState
from .nodes import (
    FormatReportNode,
    GenerateStructureNode,
    InitialSearchNode,
    InitialSummaryNode,
    ReflectionSearchNode,
    ReflectionSummaryNode,
    SaveReportNode,
)


# ── Conditional edge functions (pure, read-only state) ───────────────────


def _should_continue_reflection(state: InsightGraphState) -> str:
    count = state.get("current_reflection_count", 0)
    max_ref = state.get("max_reflections", 3)
    return "reflect_again" if count < max_ref else "next_paragraph"


def _has_more_paragraphs(state: InsightGraphState) -> str:
    idx = state.get("current_paragraph_index", 0)
    paragraphs = state.get("paragraphs", [])
    return "process_next" if idx < len(paragraphs) else "all_done"


# ── Factory ──────────────────────────────────────────────────────────────


def build_insight_graph(ctx: InsightContext) -> Any:
    """
    Build InsightEngine's LangGraph StateGraph.

    Args:
        ctx: InsightContext instance providing all dependencies.
    """
    graph = StateGraph(InsightGraphState)

    graph.add_node("generate_structure", GenerateStructureNode(ctx))
    graph.add_node("initial_search", InitialSearchNode(ctx))
    graph.add_node("initial_summary", InitialSummaryNode(ctx))
    graph.add_node("reflection_search", ReflectionSearchNode(ctx))
    graph.add_node("reflection_summary", ReflectionSummaryNode(ctx))
    graph.add_node("format_report", FormatReportNode(ctx))
    graph.add_node("persist_report", SaveReportNode(ctx))

    graph.add_edge(START, "generate_structure")
    graph.add_edge("generate_structure", "initial_search")
    graph.add_edge("initial_search", "initial_summary")
    graph.add_edge("initial_summary", "reflection_search")
    graph.add_edge("reflection_search", "reflection_summary")

    graph.add_conditional_edges(
        "reflection_summary", _should_continue_reflection,
        {"reflect_again": "reflection_search", "next_paragraph": "check_more_paragraphs"},
    )
    graph.add_node("check_more_paragraphs", lambda s: {})
    graph.add_conditional_edges(
        "check_more_paragraphs", _has_more_paragraphs,
        {"process_next": "initial_search", "all_done": "format_report"},
    )
    graph.add_edge("format_report", "persist_report")
    graph.add_edge("persist_report", END)

    return graph.compile()
