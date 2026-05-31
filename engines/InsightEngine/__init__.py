"""
InsightEngine — deep research engine using LangGraph.

Entry point: run_research() from .agent.
"""

from .agent import run_research
from app.config import settings, Settings

__version__ = "1.0.0"

__all__ = ["run_research", "settings", "Settings"]
