"""Deliver committed alignment facts to every lawful watcher's coordinator.

A checkpoint fact names the causal group of the operation that committed it
(``world.rules.presentation_events``). The coordinator is the only publication
owner, so this module registers the *observer* that forwards a committed fact to
each live watcher of the fact's actor: one forced-snapshot intent carrying the
fact's group id. The coordinator merges it with any ordinary push from the same
group, so every watcher receives one final fresh snapshot instead of an
intermediate delta, in either callback order and without an initiating session.

The fact producers (movement boundaries in M, terminal combat and completed
skips in S) call :func:`world.rules.presentation_events.emit_alignment_fact`;
nothing here mutates canonical state.
"""

from typing import Any, Callable

from world.observability import log_warn
from world.rules.presentation_events import (
    PresentationAlignmentFact,
    register_alignment_observer,
)

__all__ = ["connect_alignment_observer", "deliver_alignment_fact"]


def _resolve_actor(actor_id: int) -> Any:
    """Return the committed actor row for one fact, or ``None`` when absent."""
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(pk=actor_id).first()


def _publication_failed(
    session: Any, fact: PresentationAlignmentFact
) -> Callable[[Any], None]:
    """Build the bounded errback for one watcher's publication failure."""

    def _failed(failure: Any) -> None:
        error = getattr(failure, "value", failure)
        log_warn(
            "alignment_fact_publish_failed",
            context={
                "surface": "presentation",
                "cause": fact.cause,
                "actor": str(fact.actor_id),
                "session": str(getattr(session, "sessid", "?")),
            },
            exc=error,
        )
        return None

    return _failed


def deliver_alignment_fact(fact: PresentationAlignmentFact) -> None:
    """Forward one committed fact to every live watcher of its actor.

    Each watcher's coordinator gets one forced-snapshot intent under the fact's
    group id. A missing actor, a retired epoch or one failing session is a
    bounded diagnostic and never stops the remaining watchers.
    """
    if not isinstance(fact, PresentationAlignmentFact):
        raise TypeError("deliver_alignment_fact requires a PresentationAlignmentFact")
    actor = _resolve_actor(fact.actor_id)
    if actor is None:
        return
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.watchers import watchers_for

    try:
        watchers = watchers_for(actor)
    except Exception as error:  # observability: R2 reported here; a watcher lookup must never change committed state
        log_warn(
            "alignment_fact_watchers_failed",
            context={
                "surface": "presentation",
                "cause": fact.cause,
                "actor": str(fact.actor_id),
            },
            exc=error,
        )
        return
    for session, epoch in watchers:
        coordinator = getattr(
            getattr(session, "ndb", None), "elosern_coordinator", None
        )
        if coordinator is None or coordinator.epoch != epoch:
            continue
        try:
            deferred = coordinator.enqueue_publication(
                lambda _session=session, _actor=actor: build_presentation_context(
                    _session, _actor
                ),
                force_snapshot=True,
                expected_epoch=epoch,
                group_id=fact.group_id,
            )
        except Exception as error:  # observability: R2 reported here; one watcher must not suppress the others
            log_warn(
                "alignment_fact_publish_failed",
                context={
                    "surface": "presentation",
                    "cause": fact.cause,
                    "actor": str(fact.actor_id),
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=error,
            )
            continue
        deferred.addErrback(_publication_failed(session, fact))


def connect_alignment_observer() -> None:
    """Register the single committed-fact delivery observer (idempotent)."""
    register_alignment_observer(deliver_alignment_fact)
