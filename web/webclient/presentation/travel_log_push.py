"""Deliver committed travel facts to every lawful watcher's coordinator.

``world.rules.travel_events`` emits one immutable :class:`TravelLogFact` when
the owning operation commits. This module registers the single observer that
hands the fact to each live watcher coordinator of its actor, which attaches
the already-identified notices to the fact's causal pending group
(``PresentationCoordinator.record_travel_events``). Watchers follow the
existing movement audience policy (``watchers_for``: the session's current
puppet, including a possessed body). Nothing here mutates canonical state, and
a failing watcher never stops the others.
"""

from typing import Any, Callable

from world.observability import log_warn
from world.rules.travel_events import TravelLogFact, register_travel_observer

__all__ = ["connect_travel_log_observer", "deliver_travel_fact"]


def _resolve_actor(actor_id: int) -> Any:
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(pk=actor_id).first()


def _failed(session: Any, fact: TravelLogFact) -> Callable[[Any], None]:
    def _errback(failure: Any) -> None:
        log_warn(
            "travel_log_publish_failed",
            context={
                "surface": "presentation",
                "actor": str(fact.actor_id),
                "session": str(getattr(session, "sessid", "?")),
            },
            exc=getattr(failure, "value", failure),
        )
        return None

    return _errback


def deliver_travel_fact(fact: TravelLogFact) -> None:
    """Attach one committed fact to every live watcher's causal group."""
    if not isinstance(fact, TravelLogFact):
        raise TypeError("deliver_travel_fact requires a TravelLogFact")
    actor = _resolve_actor(fact.actor_id)
    if actor is None:
        return
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.watchers import watchers_for

    try:
        watchers = watchers_for(actor)
    except Exception as error:  # observability: R2 reported here; a watcher lookup never changes committed state
        log_warn(
            "travel_log_watchers_failed",
            context={"surface": "presentation", "actor": str(fact.actor_id)},
            exc=error,
        )
        return
    for session, epoch in watchers:
        coordinator = getattr(getattr(session, "ndb", None), "elosern_coordinator", None)
        if coordinator is None or coordinator.epoch != epoch:
            continue
        try:
            deferred = coordinator.record_travel_events(
                fact,
                lambda _session=session, _actor=actor: build_presentation_context(_session, _actor),
                expected_epoch=epoch,
            )
        except Exception as error:  # observability: R2 reported here; one watcher must not suppress the others
            log_warn(
                "travel_log_publish_failed",
                context={
                    "surface": "presentation",
                    "actor": str(fact.actor_id),
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=error,
            )
            continue
        deferred.addErrback(_failed(session, fact))


def connect_travel_log_observer() -> None:
    """Register the single committed travel-fact observer (idempotent)."""
    register_travel_observer(deliver_travel_fact)
