"""LangGraph node: build generation context for chapter writing."""

from ..state import ReportGraphState


class BuildContextNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        from ..agent import _stringify
        query = state["query"]
        reports = state.get("normalized_reports", {})
        forum_logs = state.get("forum_logs", "")
        template_result = state.get("template_result", {})
        layout = state.get("layout_design", {})
        word_plan = state.get("word_plan", {})
        template_overview = state.get("template_overview", {})

        theme = (layout.get("themeTokens") if layout else None) or _default_theme()
        chapters_map = {}
        for entry in word_plan.get("chapters", []):
            cid = entry.get("chapterId")
            if cid:
                chapters_map[cid] = entry

        ctx = {
            "query": query,
            "template_name": template_result.get("template_name"),
            "reports": reports,
            "forum_logs": _stringify(forum_logs),
            "theme_tokens": theme,
            "style_directives": {"tone": "analytical", "audience": "executive", "language": "zh-CN"},
            "data_bundles": [],
            "max_tokens": min(self.ctx.config.MAX_CONTENT_LENGTH, 6000),
            "layout": layout or {},
            "template_overview": template_overview or {},
            "chapter_directives": chapters_map,
            "word_plan": word_plan or {},
        }
        return {"generation_context": ctx}


def _default_theme() -> dict:
    return {"colors": {"bg": "#f8f9fa", "text": "#212529", "primary": "#007bff", "secondary": "#6c757d", "card": "#ffffff", "border": "#dee2e6", "accent1": "#17a2b8", "accent2": "#28a745", "accent3": "#ffc107", "accent4": "#dc3545"}, "fonts": {"body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif", "heading": "'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif"}, "spacing": {"container": "1200px", "gutter": "24px"}, "vars": {"header_sticky": True, "toc_depth": 3, "enable_dark_mode": True}}
