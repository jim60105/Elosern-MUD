"""Serialize callbacks entering the single deterministic combat writer.

Deployment has one deterministic writer process. Durable session/revision CAS
and completion receipts remain the admission authority across process restarts.
All session entry points share this reentrant lock, including terminal exits.
"""

from functools import wraps
from threading import RLock

from django.db import transaction


combat_writer = RLock()


def durable_combat_atomic():
    """The session's durable write boundary for one admission or one round.

    ``durable=True`` marks the block as the session's own commit boundary
    rather than a savepoint of an enclosing block. Django refuses to enter a
    durable block nested inside another atomic block (its only exception is a
    test case's own block), and ``initiate_field_combat()`` owns exactly such
    an outer block around engagement plus the opening seed: there the nested
    boundary takes the savepoint face, and that single outer block still
    commits or rolls back the whole unit.
    """
    blocks = transaction.get_connection().atomic_blocks
    return transaction.atomic(durable=not blocks or blocks[-1]._from_testcase)


def serialized_combat_write(function):
    """Hold admission through transaction completion and cache restoration."""
    @wraps(function)
    def serialized(*args, **kwargs):
        with combat_writer:
            return function(*args, **kwargs)
    return serialized
