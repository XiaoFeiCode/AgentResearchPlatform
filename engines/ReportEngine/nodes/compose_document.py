"""LangGraph node: compose document IR from chapters."""

from ..state import ReportGraphState


class ComposeDocumentNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        report_id = state.get("report_id", "")
        layout = state.get("layout_design", {})
        word_plan = state.get("word_plan", {})
        query = state["query"]
        template_result = state.get("template_result", {})
        template_overview = state.get("template_overview", {})
        chapters = state.get("chapters", [])

        manifest = {
            "query": query,
            "title": layout.get("title") or (f"{query} - 舆情洞察报告" if query else template_result.get("template_name")),
            "templateName": template_result.get("template_name"),
            "toc": {"depth": 3, "autoNumbering": True, "title": layout.get("tocTitle") or "目录"},
            "hero": layout.get("hero"),
        }
        if layout.get("themeTokens"):
            manifest["themeTokens"] = layout["themeTokens"]
        if layout.get("tocPlan"):
            manifest["toc"]["customEntries"] = layout["tocPlan"]
        if word_plan.get("globalGuidelines"):
            manifest["wordPlan"] = {"globalGuidelines": word_plan["globalGuidelines"]}

        doc_ir = self.ctx.document_composer.build_document(report_id, manifest, chapters)
        return {"document_ir": doc_ir}
