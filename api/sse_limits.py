"""Process-local guardrails for long-lived Server-Sent Events connections."""

from __future__ import annotations

import logging
import threading
from typing import AsyncIterator

from config import settings

logger = logging.getLogger(__name__)

_ACTIVE_CONNECTIONS = 0
_LOCK = threading.Lock()


def acquire_sse_slot() -> bool:
    """Atomically reserve a stream slot before creating a response."""
    global _ACTIVE_CONNECTIONS
    with _LOCK:
        if _ACTIVE_CONNECTIONS >= settings.MAX_SSE_CONNECTIONS:
            logger.warning(
                "SSE connection rejected: capacity reached (%d/%d)",
                _ACTIVE_CONNECTIONS,
                settings.MAX_SSE_CONNECTIONS,
            )
            return False
        _ACTIVE_CONNECTIONS += 1
        logger.info("SSE client connected. Active SSE connections: %d", _ACTIVE_CONNECTIONS)
        return True


def release_sse_slot() -> None:
    """Release a slot even when a client disconnects abruptly."""
    global _ACTIVE_CONNECTIONS
    with _LOCK:
        _ACTIVE_CONNECTIONS = max(0, _ACTIVE_CONNECTIONS - 1)
        logger.info("SSE client disconnected. Active SSE connections: %d", _ACTIVE_CONNECTIONS)


def active_sse_connections() -> int:
    with _LOCK:
        return _ACTIVE_CONNECTIONS


async def guarded_stream(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Wrap a response generator so cancellation also releases its slot."""
    try:
        async for chunk in stream:
            yield chunk
    finally:
        release_sse_slot()
