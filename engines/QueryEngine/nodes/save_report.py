"""LangGraph node: persist report to disk."""

import os
from datetime import datetime
from loguru import logger
from ..state import QueryGraphState
from ..models.state import Paragraph, State


class SaveReportNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: QueryGraphState) -> dict:
        self._pc({"status": "saving", "message": "正在保存报告...", "progress_pct": 95})
        if not state.get("save_report", True):
            return {}
        report, query = state.get("final_report", ""), state.get("query", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in query if c.isalnum() or c in (" ", "-", "_")).rstrip().replace(" ", "_")[:30]
        fp = os.path.join(self.ctx.config.OUTPUT_DIR, f"deep_search_report_{safe}_{ts}.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存到: {fp}")
        if self.ctx.config.SAVE_INTERMEDIATE_STATES:
            ds = _rebuild(report, query, state)
            ds.save_to_file(os.path.join(self.ctx.config.OUTPUT_DIR, f"state_{safe}_{ts}.json"))
        return {}

    def _pc(self, data):
        if self.ctx.progress_callback:
            self.ctx.progress_callback(data)


def _rebuild(final_report: str, query: str, gs: QueryGraphState) -> State:
    return State(query=query, report_title=gs.get("report_title", ""), paragraphs=[Paragraph.from_dict(d) for d in gs.get("paragraphs", [])], final_report=final_report, is_completed=True)
