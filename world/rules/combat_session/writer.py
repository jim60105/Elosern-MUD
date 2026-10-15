"""Serialize callbacks entering the single deterministic combat writer.

Deployment has one deterministic writer process. Durable session/revision CAS
and completion receipts remain the admission authority across process restarts.
All session entry points share this reentrant lock, including terminal exits.
"""

from functools import wraps
from threading import RLock


combat_writer = RLock()


def serialized_combat_write(function):
    """Hold admission through transaction completion and cache restoration."""
    @wraps(function)
    def serialized(*args, **kwargs):
        with combat_writer:
            return function(*args, **kwargs)
    return serialized
