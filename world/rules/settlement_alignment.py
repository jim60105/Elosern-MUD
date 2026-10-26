"""Committed terminal-combat and completed-skip alignment checkpoints.

The deterministic combat settlement and the time-skip owners are the only places
a terminal encounter or a completed explicit interval is known to have
committed, so they are also the only places these checkpoint facts may be
captured (webclient-settlement-alignment). Capture is read-only: nothing here
mutates game state, builds a publication, or imports the webclient.

Two rules make one settlement produce one final publication rather than a delta
followed by a correction:

- ``checkpoint_owner`` binds one causal publication group around a whole
  synchronous owner before its transaction starts, so every ordinary push and
  every nested checkpoint the owner causes carries the same identity.
- The emission itself is registered on the owning commit, so a refused,
  rolled-back or replayed operation publishes nothing.

A caller never decides a checkpoint from an action name, a request type or a
``mode`` change: it only reaches these producers from a committed fact.
"""

from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, TypeVar

from world.rules.presentation_events import (
    PresentationAlignmentFact,
    current_publication_group,
    emit_alignment_fact,
    new_publication_group,
    on_publication_commit,
    publication_group,
)

__all__ = [
    "AWAKENED_SKIP",
    "COMBAT_TERMINAL",
    "checkpoint_owner",
    "publish_awake_skip",
    "publish_combat_terminal",
    "publish_completed_sleep",
]

#: The alignment cause of one committed combat termination.
COMBAT_TERMINAL = "combat_terminal"

#: The alignment cause of one completed explicit rest/sleep/time skip.
AWAKENED_SKIP = "skip_completed"

_Owner = TypeVar("_Owner", bound=Callable[..., Any])


def checkpoint_owner(function: _Owner) -> _Owner:
    """Bind one causal publication group around a whole synchronous owner.

    The group is opened *before* the owner's transaction and nested effects, so
    a clock push, a movement checkpoint or an ordinary panel update caused by
    the same operation merges into the one final publication instead of
    preceding it as its own delta. A nested owner (a continuation settlement
    inside a larger skip, a terminal settlement inside a round) reuses the
    caller's group.
    """

    @wraps(function)
    def scoped(*args: Any, **kwargs: Any) -> Any:
        with publication_group():
            return function(*args, **kwargs)

    return scoped  # type: ignore[return-value]


def _emit_on_commit(actor_id: int, cause: str) -> None:
    """Register one checkpoint fact for the surrounding committed transaction."""

    def _committed() -> None:
        group = current_publication_group() or new_publication_group()
        emit_alignment_fact(
            PresentationAlignmentFact(
                group_id=group.id,
                actor_id=actor_id,
                cause=cause,
            )
        )

    on_publication_commit(_committed)


def _identity_id(actor: Any) -> int | None:
    """The integer primary key that names a lawful alignment target.

    A synthetic fixture without a row identity has no watcher to align, so it
    simply publishes nothing rather than inventing a target.
    """
    raw = getattr(actor, "pk", None)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def publish_combat_terminal(actor: Any, participant_ids: Iterable[Any] = ()) -> None:
    """Publish one committed terminal-combat checkpoint per lawful target.

    The acting character and every recorded player participant each receive a
    fact: watchers are indexed under the session's *current puppet*, which is
    the acting character itself or the companion it possesses, never the
    commander whose durable session every party member shares. A fact for an
    identity nobody watches is a no-op in the delivery observer.

    Call this only from the deterministic owner of a newly committed terminal
    settlement, after its final clear and terminal writes; a replayed or
    nonterminal settlement calls it never.
    """
    acting = _identity_id(actor)
    identities: list[int] = [] if acting is None else [acting]
    for participant in participant_ids:
        identity = int(participant)
        if identity not in identities:
            identities.append(identity)
    for identity in identities:
        _emit_on_commit(identity, COMBAT_TERMINAL)


def publish_awake_skip(actor: Any, result: Any) -> bool:
    """Publish one checkpoint for a completed explicit awake skip.

    Qualifies exactly when the accepted operation actually settled a positive
    interval and is not a replay of an already committed receipt. A truncated
    or partial interval that ends the accepted request qualifies (the remainder
    is discarded, nothing continues); a zero-time wait, a refusal, a rolled-back
    advance or a duplicate receipt does not. Return whether it qualified.
    """
    if getattr(result, "replayed", False):
        return False
    if int(getattr(result, "elapsed_seconds", 0) or 0) <= 0:
        return False
    actor_id = _identity_id(actor)
    if actor_id is None:
        return False
    _emit_on_commit(actor_id, AWAKENED_SKIP)
    return True


def publish_completed_sleep(actor: Any, result: Any) -> bool:
    """Publish one checkpoint for a newly completed accepted sleep operation.

    The owning result is the only authority: posture, a positive elapsed time,
    the request type or the wake message never substitute for it. A retained
    continuation is not completed, and a replayed receipt was already
    published, so neither qualifies. Return whether it qualified.
    """
    if getattr(result, "replayed", False):
        return False
    if not getattr(result, "completed", False):
        return False
    actor_id = _identity_id(actor)
    if actor_id is None:
        return False
    _emit_on_commit(actor_id, AWAKENED_SKIP)
    return True
