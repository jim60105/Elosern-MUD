"""Serialize callbacks entering the single deterministic combat writer.

Deployment has one deterministic writer process. Durable session/revision CAS
and completion receipts remain the admission authority across process restarts.
All session entry points share this reentrant lock, including terminal exits.
"""

from functools import wraps
from threading import RLock

from django.db import transaction


combat_writer = RLock()


def durable_combat_atomic(*, nested: bool = False):
    """The session's durable write boundary for one admission or one round.

    ``durable=True`` marks the block as the session's real commit boundary
    rather than a savepoint of an enclosing block, and Django refuses to enter
    a durable block inside another atomic block. A caller that legitimately
    owns an outer unit declares ``nested=True``: ``initiate_field_combat()``
    spans engagement plus the opening seed in one ``transaction.atomic()``,
    and there the nested boundary takes the savepoint face of that single
    unit, which still commits or rolls back the whole thing. Every other
    nested entry keeps raising, which is what the admission contract relies on
    (``test_nested_caller_transaction_rejects_before_admission``).
    """
    return transaction.atomic(durable=not nested)


def serialized_combat_write(function):
    """Hold admission through transaction completion and cache restoration."""
    @wraps(function)
    def serialized(*args, **kwargs):
        with combat_writer:
            return function(*args, **kwargs)
    return serialized
