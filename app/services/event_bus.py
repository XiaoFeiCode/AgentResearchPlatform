"""Publish/subscribe event bus — framework-agnostic event distribution.

Services publish events here. SSE routers register handlers to forward events to clients.
"""

import threading
from typing import Any, Callable, Dict, List

EventCallback = Callable[[str, Dict[str, Any]], None]

_lock = threading.Lock()
_subscribers: List[EventCallback] = []


def publish(event_type: str, data: Dict[str, Any]) -> None:
    """Publish an event to all registered subscribers."""
    with _lock:
        
        subs = list(_subscribers)
    for callback in subs:
        try:
            callback(event_type, data)
        except Exception:
            pass  # subscriber errors must not propagate to publishers


def subscribe(callback: EventCallback) -> None:
    """Register a subscriber that will receive all events."""
    with _lock:
        if callback not in _subscribers:
            _subscribers.append(callback)


def unsubscribe(callback: EventCallback) -> None:
    """Remove a previously registered subscriber."""
    with _lock:
        try:
            _subscribers.remove(callback)
        except ValueError:
            pass


def clear() -> None:
    """Remove all subscribers (useful for testing)."""
    with _lock:
        _subscribers.clear()
