"""LangGraph node: slice template into sections."""

from loguru import logger
from ..state import ReportGraphState
from ..core import parse_template_sections, TemplateSection


class SliceTemplateNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        template_content = state.get("template_result", {}).get("template_content", "")
        sections = parse_template_sections(template_content)
        if not sections:
            logger.warning("模板未解析出章节，使用默认章节骨架")
            sections = [TemplateSection(title="1.0 综合分析", slug="section-1-0", order=10, depth=1, raw_title="1.0 综合分析", number="1.0", chapter_id="S1", outline=["1.1 摘要", "1.2 数据亮点", "1.3 风险提示"])]
        # Build template_overview
        overview = {"title": _extract_title(template_content, sections[0].title if sections else ""), "chapters": []}
        for s in sections:
            overview["chapters"].append({"chapterId": s.chapter_id, "title": s.title, "rawTitle": s.raw_title, "number": s.number, "slug": s.slug, "order": s.order, "depth": s.depth, "outline": s.outline})
        return {"template_sections": sections, "template_overview": overview}


def _extract_title(md: str, fallback: str = "") -> str:
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
        if s:
            fallback = fallback or s
    return fallback or "智能舆情分析报告"
