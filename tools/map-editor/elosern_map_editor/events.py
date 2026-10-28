"""Server-sent invalidation/status notifications.

The stream never carries world data: a client that sees ``invalidate`` (or
reconnects and sees a ``status`` with a newer revision or another session)
fetches ``GET /api/workspace`` again and replaces its whole state.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

_CLOSE = object()


def format_event(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, sort_keys=True)}\n\n".encode("utf-8")


class Broadcaster:
    """Per-client bounded queues; a slow client is dropped and must reconnect."""

    def __init__(self, queue_size: int = 16) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._queue_size = queue_size
        self._closed = False

    @property
    def client_count(self) -> int:
        return len(self._queues)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        message = format_event(event, data)
        for queue in tuple(self._queues):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Dropping the client forces a reconnect, which refetches.
                self._queues.discard(queue)
                _force_close(queue)

    def close(self) -> None:
        """End every open stream (service shutdown)."""

        self._closed = True
        for queue in tuple(self._queues):
            _force_close(queue)
        self._queues.clear()

    async def stream(
        self, first: Callable[[], bytes], heartbeat_seconds: float
    ) -> AsyncIterator[bytes]:
        queue: asyncio.Queue = asyncio.Queue(self._queue_size)
        if self._closed:
            return
        self._queues.add(queue)
        # The first status is taken only after the queue is registered, with no
        # await in between, so no invalidation can fall between the two.
        opening = first()
        try:
            yield b"retry: 2000\n\n" + opening
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), heartbeat_seconds)
                except TimeoutError:
                    yield b": keep-alive\n\n"
                    continue
                if message is _CLOSE:
                    return
                yield message
        finally:
            self._queues.discard(queue)


def _force_close(queue: asyncio.Queue) -> None:
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            break
    queue.put_nowait(_CLOSE)


__all__ = ["Broadcaster", "format_event"]
