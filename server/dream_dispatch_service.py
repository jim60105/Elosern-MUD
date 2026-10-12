"""Composition root for the dream-dispatch background pump.

The pump is the game server's single owner of background dispatch work. It lives
in ``server/`` because that is the one place where both import directions are
legal: it constructs the generated-content clients (``world.ai``) and drives the
deterministic stage runner (``world.narrative``).

Lifecycle, and why each part is here:

* :func:`start_pump` is called from ``at_server_start`` after the director
  layers are registered and persisted sessions are restored: it registers the
  wake-up hint, fences and resumes interrupted claims, re-arms waiting work and
  kicks once. It is idempotent, so a reload's second start is harmless.
* :func:`stop_pump` is called from the shutdown and reload-stop hooks: it stops
  claiming, unregisters the hint and fences outstanding claims, so an unfinished
  callback that outlives the stop cannot mutate work, publication or dialogue.
* :func:`kick` is the notification seam. A kick while a generation is in flight
  only records that another pass is wanted, so at most one generation ever runs;
  the queue is drained by one pass at a time, and a pass that finds nothing
  eligible ends the chain (no polling, no retry scheduler).
* The portal never loads this module's hooks, so no portal guard is needed.

A model call never runs inside a database transaction: the runner awaits outside
every transaction and persists through the work records' short ones.
"""

from __future__ import annotations

from typing import Any, Optional

from twisted.python.failure import Failure
from twisted.internet import defer

from world.narrative import dispatch
from world.narrative.dispatch_runner import StageClients, run_next
from world.observability import log_info, log_warn

__all__ = [
    "build_story_director_client",
    "capability_enabled",
    "kick",
    "pump_state",
    "start_pump",
    "stop_pump",
]


class _OfflineStubClient:
    """The non-``None`` client injected while a capability is disabled.

    The capability check skips a disabled stage before any transport work, so
    this client is never called; if it ever is, it fails loudly instead of
    silently half-opening a connection.
    """

    def get_response(self, descriptor):
        raise AssertionError(
            "offline stub client must never be called; a disabled stage is "
            "skipped by the capability check"
        )


_STATE: dict[str, bool] = {
    "running": False,
    "in_flight": False,
    "pending": False,
    "stopped": False,
}


def pump_state() -> dict[str, bool]:
    """A read-only view of the pump's flags (tests and operators)."""
    return dict(_STATE)


def reset_pump_state() -> None:
    """Clear the in-process flags; used by tests that drive the pump directly."""
    _STATE.update(running=False, in_flight=False, pending=False, stopped=False)


def build_story_director_client() -> Any:
    """Construct this capability's client, never reuse another layer profile."""
    from world.ai.profiles import get_profile

    profile = get_profile("story_director")
    if not profile.enabled:
        return _OfflineStubClient()
    from world.ai.client import OpenAICompatClient

    return OpenAICompatClient(profile)


def capability_enabled(name: str) -> bool:
    """Whether one stage's configured capability is available right now."""
    from world.ai.profiles import get_profile

    try:
        return bool(get_profile(name).enabled)
    except Exception:
        # observability: ignore R2: an unknown layer is an unavailable capability, not a crash
        return False


def start_pump() -> Optional[bool]:
    """Start the pump: register the hint, recover, reconsider and kick once.

    Returns ``True`` when this call started the pump and ``None`` when it was
    already running. It never returns ``False``: the startup step wrapper reads
    a ``False`` return as a tolerated skip and would emit no ``startup_step``
    event for the step.
    """
    if _STATE["running"]:
        return None
    dispatch.register_pump(kick)
    recovered = dispatch.recover_interrupted()
    waiting = dispatch.consider_waiting()
    _STATE.update(running=True, in_flight=False, pending=False, stopped=False)
    log_info(
        "dream_dispatch_pump_started",
        context={"recovered": len(recovered), "waiting": waiting},
    )
    kick()
    return True


def stop_pump() -> bool:
    """Stop claiming (unregister the hint) and fence unfinished callbacks."""
    was_running = _STATE["running"]
    _STATE.update(running=False, in_flight=False, pending=False, stopped=True)
    dispatch.register_pump(None)
    fenced = dispatch.fence_all()
    log_info("dream_dispatch_pump_stopped", context={"fenced": fenced})
    return was_running


def kick() -> None:
    """Wake the pump. At most one generation runs at a time."""
    if not _STATE["running"] or _STATE["stopped"]:
        return
    if _STATE["in_flight"]:
        # A pass is already running; remember that another one is wanted.
        _STATE["pending"] = True
        return
    _STATE["in_flight"] = True
    deferred = _drain()
    deferred.addBoth(_complete)


def _complete(result: Any) -> Any:
    """Finish one pass and continue the drain exactly while work remains."""
    _STATE["in_flight"] = False
    if isinstance(result, Failure):
        log_warn(
            "dream_dispatch_pump_failed",
            context={},
            exc=result.value,
        )
        result = None
    if _STATE["running"] and not _STATE["stopped"]:
        more = _STATE["pending"] or (
            getattr(result, "outcome", "no_work") != "no_work"
        )
        _STATE["pending"] = False
        if more:
            kick()
    return result


@defer.inlineCallbacks
def _drain():
    """Run one pass: build the injected clients once, then process one record.

    The clients are constructed per pass so a runtime profile change is picked
    up on the next kick without holding any transport across passes.
    """
    from server.ai_director_service import build_scenario_director_client

    clients = StageClients(
        story=build_story_director_client(),
        scenario=build_scenario_director_client(),
    )
    result = yield run_next(clients=clients, capability_enabled=capability_enabled)
    if result.outcome == "arranged":
        # Post-commit only: the publication transaction has already committed,
        # so a failed activation or notice can never undo it.
        after_arranged(result.dispatch_id)
    defer.returnValue(result)


def _connected_actor(owner_id: str) -> Optional[Any]:
    """The saved owner's current lawful actor, or ``None`` when offline."""
    from world.narrative.dispatch_status import current_owner_id
    from world.quests.encounter_dispatch import puppeted_characters

    for actor in puppeted_characters():
        if current_owner_id(actor) == owner_id:
            return actor
    return None


def after_arranged(dispatch_id: str) -> bool:
    """Post-commit effects of one arrangement: activate and tell the truth.

    Runs strictly after the publication transaction committed. An offline owner
    needs no actor movement and no invented appearance: its durable state stays,
    and reconnect reads the latest status and the actual scene.
    """
    work = dispatch.find_work(dispatch_id)
    if work is None:
        return False
    actor = _connected_actor(work.owner_id)
    if actor is None:
        return False
    from world.narrative import dispatch_status
    from world.quests.encounter_dispatch import activate_pending_encounters
    from world.rules.clock import get_world_clock

    activate_pending_encounters(
        actor,
        room=getattr(actor, "location", None),
        tick=int(get_world_clock().tick),
    )
    dispatch_status.deliver_status(actor)
    return True
