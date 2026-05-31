"""ReportEngine LangGraph 图定义。build_report_graph(ctx) 构建 StateGraph。"""

from typing import Any
from langgraph.graph import END, START, StateGraph
from .context import ReportContext
from .state import ReportGraphState
from .nodes import (
    NormalizeReportsNode, SelectTemplateNode, SliceTemplateNode,
    DesignLayoutNode, PlanBudgetNode, BuildContextNode,
    GenerateChaptersNode, ComposeDocumentNode,
    RenderHtmlNode, SaveReportNode,
)


def build_report_graph(ctx: ReportContext) -> Any:
    graph = StateGraph(ReportGraphState)

    graph.add_node("normalize", NormalizeReportsNode(ctx))
    graph.add_node("select_template", SelectTemplateNode(ctx))
    graph.add_node("slice_template", SliceTemplateNode(ctx))
    graph.add_node("design_layout", DesignLayoutNode(ctx))
    graph.add_node("plan_budget", PlanBudgetNode(ctx))
    graph.add_node("build_context", BuildContextNode(ctx))
    graph.add_node("generate_chapters", GenerateChaptersNode(ctx))
    graph.add_node("compose", ComposeDocumentNode(ctx))
    graph.add_node("render", RenderHtmlNode(ctx))
    graph.add_node("save", SaveReportNode(ctx))

    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "select_template")
    graph.add_edge("select_template", "slice_template")
    graph.add_edge("slice_template", "design_layout")
    graph.add_edge("design_layout", "plan_budget")
    graph.add_edge("plan_budget", "build_context")
    graph.add_edge("build_context", "generate_chapters")
    graph.add_edge("generate_chapters", "compose")
    graph.add_edge("compose", "render")
    graph.add_edge("render", "save")
    graph.add_edge("save", END)

    return graph.compile()
