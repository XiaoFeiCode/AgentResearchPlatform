"""
ForumEngine — event-driven forum handler.

Subscribes to summary_ready events from search engines and manages
forum session, HOST speech generation, and forum.log persistence.
"""

from .handler import ForumEventHandler

__all__ = ['ForumEventHandler']
