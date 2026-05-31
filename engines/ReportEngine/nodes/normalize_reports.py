"""LangGraph node: normalize reports from input list to dict."""

from ..state import ReportGraphState


class NormalizeReportsNode:
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, state: ReportGraphState) -> dict:
        from ..agent import _stringify
        reports = state.get("reports", [])
        keys = ["query_engine", "media_engine", "insight_engine"]
        engine_names = {"query_engine": "QueryEngine", "media_engine": "MediaEngine", "insight_engine": "InsightEngine"}
        normalized = {}
        for idx, key in enumerate(keys):
            value = reports[idx] if idx < len(reports) else ""
            text = _stringify(value)
            if not text or not text.strip():
                text = f"【{engine_names[key]} 未启动，本次报告无该引擎的分析数据】"
            normalized[key] = text
        return {"normalized_reports": normalized}
