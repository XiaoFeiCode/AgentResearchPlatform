"""
LangGraph node: persist report to disk.
"""

import os
from datetime import datetime

from loguru import logger

from ..state import MediaGraphState
from ..models.state import Paragraph, State


class SaveReportNode:
    """Save the final report and optional intermediate state to disk."""

    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: MediaGraphState) -> dict:
        self._pc({"status": "saving", "message": "正在保存报告...", "progress_pct": 95})
        if not state.get("save_report", True):
            return {}

        final_report = state.get("final_report", "")
        query = state.get("query", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in query if c.isalnum() or c in (" ", "-", "_")).rstrip().replace(" ", "_")[:30]

        filename = f"deep_search_report_{safe}_{ts}.md"
        filepath = os.path.join(self.ctx.config.OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_report)
        logger.info(f"报告已保存到: {filepath}")

        if self.ctx.config.SAVE_INTERMEDIATE_STATES:
            dc_state = _rebuild_state_from_graph(state)
            dc_state.final_report = final_report
            dc_state.is_completed = True
            dc_state.save_to_file(os.path.join(self.ctx.config.OUTPUT_DIR, f"state_{safe}_{ts}.json"))

        return {}

    def _pc(self, data: dict):
        if self.ctx.progress_callback:
            self.ctx.progress_callback(data)


def _rebuild_state_from_graph(graph_state: MediaGraphState) -> State:
    paragraphs = [Paragraph.from_dict(d) for d in graph_state.get("paragraphs", [])]
    return State(
        query=graph_state.get("query", ""),
        report_title=graph_state.get("report_title", ""),
        paragraphs=paragraphs,
        final_report=graph_state.get("final_report", ""),
        is_completed=graph_state.get("is_completed", False),
    )
