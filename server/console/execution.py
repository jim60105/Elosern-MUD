"""One synchronous gameplay-thread boundary, with no snapshot I/O."""

from threading import local
from typing import Callable, TypeVar

from server.console.errors import ConsoleError

T = TypeVar("T")
_context = local()


def in_handoff() -> bool:
    return bool(getattr(_context, "active", False))


def guarded(operation: Callable[[], T]) -> T:
    """Mark even injected runners so an owner cannot re-enter coordination."""
    if in_handoff():
        raise ConsoleError("snapshot_failed", "console_in_progress")
    _context.active = True
    try:
        return operation()
    finally:
        _context.active = False


def run_on_gameplay_thread(operation: Callable[[], T]) -> T:
    """Hand off while the reactor runs; inline only when gameplay is stopped."""
    from twisted.internet import reactor, threads
    from twisted.python.threadable import isInIOThread

    if in_handoff() or (reactor.running and isInIOThread()):
        raise ConsoleError("snapshot_failed", "console_in_progress")
    if reactor.running:
        return threads.blockingCallFromThread(reactor, operation)
    return operation()
