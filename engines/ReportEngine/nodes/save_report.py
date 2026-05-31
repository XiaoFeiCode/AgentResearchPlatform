"""LangGraph node: persist report to disk."""

import os, json
from datetime import datetime
from pathlib import Path
from loguru import logger
from ..state import ReportGraphState
from ..models.state import ReportState, ReportMetadata


class SaveReportNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        if not state.get("save_report", True):
            return {}
        html = state.get("html_content", "")
        doc_ir = state.get("document_ir", {})
        query = state["query"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in query if c.isalnum() or c in (" ", "-", "_")).rstrip().replace(" ", "_")[:30] or "report"

        html_path = Path(self.ctx.config.OUTPUT_DIR) / f"final_report_{safe}_{ts}.html"
        html_path.write_text(html, encoding="utf-8")

        ir_path = Path(self.ctx.config.DOCUMENT_IR_OUTPUT_DIR) / f"report_ir_{safe}_{ts}.json"
        ir_path.parent.mkdir(parents=True, exist_ok=True)
        ir_path.write_text(json.dumps(doc_ir, ensure_ascii=False, indent=2), encoding="utf-8")

        state_obj = ReportState(task_id=state.get("report_id", ""), query=query, status="completed", html_content=html, metadata=ReportMetadata(query=query, template_used=state.get("template_result", {}).get("template_name", "")))
        state_path = Path(self.ctx.config.OUTPUT_DIR) / f"report_state_{safe}_{ts}.json"
        state_obj.save_to_file(str(state_path))

        result = {"report_filename": html_path.name, "report_filepath": str(html_path.resolve()), "ir_filename": ir_path.name, "ir_filepath": str(ir_path.resolve()), "state_filename": state_path.name, "state_filepath": str(state_path.resolve())}
        logger.info(f"报告已保存: {html_path}")
        return {"saved_files": result}
