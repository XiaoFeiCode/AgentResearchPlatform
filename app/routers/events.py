"""
SSE event stream — replaces Socket.IO for real-time communication.

Publishes: console_output, forum_message, status_update
"""

import asyncio
import json
import threading
import time
from collections import deque
from queue import Queue, Empty

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse
from loguru import logger

from app.services.event_bus import subscribe, unsubscribe

router = APIRouter(tags=["events"])

# Per-subscriber queues (one per SSE connection)
_subscribers: list[Queue] = []
_subscribers_lock = threading.Lock()

# Ring buffer of recent events for replay on reconnect
REPLAY_EVENT_TYPES = {"engine_result", "engine_progress"}
_replay_buffer: deque = deque(maxlen=300)
_replay_lock = threading.Lock()

# Per-engine latest engine_result (for guaranteed delivery even if buffer wraps)
_latest_results: dict[str, str] = {}  # engine_name → SSE payload
_latest_results_lock = threading.Lock()


def _event_bus_forwarder(event_type: str, data: dict):
    """Forward event to ALL subscriber queues + replay buffer."""
    payload = json.dumps({"event": event_type, "data": data}, ensure_ascii=False)

    # Store in replay buffer for new/reconnected clients
    if event_type in REPLAY_EVENT_TYPES:
        with _replay_lock:
            _replay_buffer.append(payload)

    # Track latest engine_result per engine (never expires)
    if event_type == "engine_result":
        engine = data.get("engine", "")
        if engine:
            with _latest_results_lock:
                _latest_results[engine] = payload

    # Forward to all live subscribers
    with _subscribers_lock:
        queues = list(_subscribers)
    for q in queues:
        try:
            q.put_nowait(payload)
        except Exception:
            pass


def init_event_stream():
    """Register the SSE forwarder with the EventBus."""
    subscribe(_event_bus_forwarder)


def shutdown_event_stream():
    """Unregister the SSE forwarder and clear in-memory SSE state."""
    unsubscribe(_event_bus_forwarder)
    with _subscribers_lock:
        _subscribers.clear()
    with _replay_lock:
        _replay_buffer.clear()
    with _latest_results_lock:
        _latest_results.clear()


def _register() -> Queue:
    q: Queue = Queue()
    with _subscribers_lock:
        _subscribers.append(q)
    return q


def _unregister(q: Queue):
    with _subscribers_lock:
        if q in _subscribers:
            _subscribers.remove(q)


def _get_replay_events() -> list[str]:
    """Get buffered events to replay for a new connection."""
    events: list[str] = []

    # Always include latest per-engine results (even if buffer wrapped)
    with _latest_results_lock:
        for engine in ("insight", "media", "query"):
            if engine in _latest_results:
                events.append(_latest_results[engine])

    # Also replay recent buffer events (for progress context)
    with _replay_lock:
        buffered = list(_replay_buffer)

    # Merge: buffer events first (progress timeline), then latest results.
    # Deduplicate while preserving the first occurrence. Do not pre-seed with
    # latest results; doing so drops engine_result replay for refreshed clients.
    seen = set()
    merged = buffered + events
    return [e for e in merged if not (e in seen or seen.add(e))]


async def _event_generator(request: Request):
    """SSE event generator with keepalive, replay buffer, and per-connection queue."""

    q = _register()
    logger.debug("SSE client connected")

    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        # Replay recent events for reconnected clients
        replay = _get_replay_events()
        if replay:
            logger.debug(f"SSE replaying {len(replay)} buffered events")
            for payload in replay:
                yield f"data: {payload}\n\n"

        last_event_time = time.time()
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = q.get(timeout=1)
                yield f"data: {payload}\n\n"
                last_event_time = time.time()
            except Empty:
                if time.time() - last_event_time > 15:
                    yield ": keepalive\n\n"
                    last_event_time = time.time()
    finally:
        _unregister(q)
        logger.debug("SSE client disconnected")


@router.get("/api/events/stream")
async def event_stream(request: Request):
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
