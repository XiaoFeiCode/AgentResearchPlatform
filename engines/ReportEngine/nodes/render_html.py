"""LangGraph node: render HTML from document IR."""

from loguru import logger
from ..state import ReportGraphState


class RenderHtmlNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        doc_ir = state.get("document_ir", {})
        html = self.ctx.renderer.render(doc_ir)
        logger.info(f"HTML 渲染完成: {len(html)} 字符")
        return {"html_content": html}
