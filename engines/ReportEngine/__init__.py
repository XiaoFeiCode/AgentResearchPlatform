"""
ReportEngine — intelligent report generation using LangGraph.

Entry point: generate_report() from .agent.
"""

from .agent import generate_report

__version__ = "1.0.0"

__all__ = ["generate_report"]
