"""
LangGraph node: persist report to disk.
"""

import json
import os
from datetime import datetime

from loguru import logger

from ..state import InsightGraphState
from ..context import InsightContext


class SaveReportNode:
    """Save the final report and optional intermediate state to disk."""

    def __init__(self, ctx):
        self.ctx: InsightContext = ctx

    def __call__(self, state: InsightGraphState) -> dict:
        self.ctx.progress_callback({"status": "saving", "message": "正在保存报告...", "progress_pct": 95})
        if not state.get("save_report", True):
            return {}

        final_report = state.get("final_report", "")
        query = state.get("query", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in query if c.isalnum() or c in (" ", "-", "_")).rstrip().replace(" ", "_")[:30]

        # Save .md report
        filename = f"deep_search_report_{safe}_{ts}.md"
        filepath = os.path.join(self.ctx.config.OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_report)
        logger.info(f"报告已保存到: {filepath}")

        # Save state JSON (optional)
        if self.ctx.config.SAVE_INTERMEDIATE_STATES:
            state_file = os.path.join(self.ctx.config.OUTPUT_DIR, f"state_{safe}_{ts}.json")
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(dict(state), f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"状态已保存到: {state_file}")

        return {
            "status": "completed",
            "report_file": filepath,
        }
