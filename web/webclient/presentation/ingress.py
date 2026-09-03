"""Server-side ingress and post-command refresh helpers for the OOB protocol.

These helpers isolate the Evennia session plumbing from the pure protocol and
coordinator modules: the input functions in ``server/conf/inputfuncs.py`` stay
thin and delegate authentication, synchronization, protocol-error emission, and
post-command refresh here.
"""

from copy import deepcopy
from types import MappingProxyType
from typing import Any

from twisted.internet.defer import Deferred

from web.webclient.presentation.context import (
    FrozenCard,
    OptionsSnapshot,
    ProposalSnapshot,
    PresentationContext,
)
from web.webclient.presentation.coordinator import (
    ClockUnavailable,
    PresentationCoordinator,
    attach_coordinator,
    log_unavailable,
)
from web.webclient.presentation.protocol import (
    PROTOCOL_VERSION,
    UI_PROTOCOL_ERROR,
    check_envelope,
)
from web.webclient.presentation.registry import build_production_registry

# The only transport that may receive Elosern graphical OOB state. Evennia 6.1
# portal sessions pass "websocket" to ``init_session``, which overwrites the
# class-level "webclient/websocket" label, so real sessions report "websocket";
# both spellings are accepted.
_WEBSOCKET_PROTOCOLS = frozenset({"websocket", "webclient/websocket"})
_AJAX_PROTOCOL = "webclient/ajax"


def is_webclient(session: Any) -> bool:
    """Return whether ``session`` is the evennia WebSocket WebClient."""
    return getattr(session, "protocol_key", None) in _WEBSOCKET_PROTOCOLS


def is_ajax_webclient(session: Any) -> bool:
    """Return whether ``session`` is the legacy AJAX WebClient."""
    return getattr(session, "protocol_key", None) == _AJAX_PROTOCOL


def send_protocol_error(
    session: Any,
    *,
    code: str,
    message: str,
    reload_required: bool,
    correlation_id: str | None = None,
) -> None:
    """Emit one exact ``ui_protocol_error`` envelope to a session."""
    envelope: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
        "reload_required": reload_required,
    }
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    session.msg(**{UI_PROTOCOL_ERROR: ((envelope,), {})})


def _coordinator_for(session: Any, actor: Any) -> PresentationCoordinator:
    """Return the session's ephemeral coordinator, reset on puppet change.

    A puppet change atomically retires the previous presentation sequence AND
    the previous dispatch sequence (request cache and in-flight marker), so a
    completion Deferred started for the old puppet can never publish a result
    or panel state into the new puppet's sequence.
    """
    coordinator = attach_coordinator(session, build_production_registry())
    actor_id = str(getattr(actor, "pk", ""))
    last_actor = getattr(session.ndb, "elosern_actor_id", None)
    if last_actor is not None and last_actor != actor_id:
        # A puppet change starts a distinct presentation sequence and drops the
        # previous character's options state (the new puppet never inherits the
        # old one's fingerprint, cards, or degraded status) and its dismissal
        # barriers (a dismissed minimum generation is per character).
        coordinator.reset()
        session.ndb.options_state = None
        session.ndb.options_barriers = None
        # The transient concept proposal belongs to the old puppet exactly
        # like the options state: the new puppet never sees it.
        session.ndb.concept_proposal = None
        from web.webclient.actions.dispatcher import retire_sequence

        retire_sequence(session)
    session.ndb.elosern_actor_id = actor_id
    return coordinator


def send_unpuppet_transition(session: Any) -> None:
    """Notify a WebClient that its puppet detached, before the sequence retires.

    The browser clears character panels and locks mutations on this signal, so
    it must be delivered while the session is still a live WebClient. Telnet
    and AJAX sessions receive no graphical OOB state.
    """
    if not is_webclient(session):
        return
    send_protocol_error(
        session,
        code="no_puppet",
        message="你已離開角色（OOC）。",
        reload_required=False,
    )


def reset_client_sequence(session: Any) -> None:
    """Start a fresh client-visible sequence for the next puppet.

    Bumps the attached coordinator's epoch and clears the recorded actor
    binding, so repuppeting the same character later still produces a fresh
    epoch and never reuses the retired dispatch cache or in-flight marker.
    """
    coordinator = attach_coordinator(session, build_production_registry())
    coordinator.reset()
    if getattr(session, "ndb", None) is not None:
        session.ndb.elosern_actor_id = None
        session.ndb.options_state = None
        session.ndb.options_barriers = None
        session.ndb.concept_proposal = None


def options_snapshot(session: Any) -> OptionsSnapshot | None:
    """Return an immutable snapshot of ``session.ndb.options_state``, or ``None``.

    The write side (the trigger service) populates ``session.ndb.options_state``
    as a dict carrying ``owner_actor_id``, ``fingerprint``, ``status``,
    ``generation_token``, and ``displayed``; this read-side factory deep-copies
    the displayed cards into frozen :class:`FrozenCard` representations so a
    presenter's render is stable even if the async writer later replaces the
    session state object. An absent state (the common case until the trigger
    service lands) yields ``None``, as does any malformed state — this factory
    must never raise on the ingress/dispatcher publication path, so a corrupt
    ephemeral write degrades to an inert snapshot rather than an internal
    presentation error.
    """
    ndb = getattr(session, "ndb", None)
    state = getattr(ndb, "options_state", None) if ndb is not None else None
    if state is None:
        return None
    try:
        return _build_options_snapshot(session, state)
    except Exception:
        log_unavailable("options snapshot", "malformed options_state degraded to None")
        return None


def _build_options_snapshot(session: Any, state: Any) -> OptionsSnapshot | None:
    if not isinstance(state, dict):
        return None
    owner = state.get("owner_actor_id")
    if owner is not None:
        actor = getattr(session, "puppet", None)
        if str(getattr(actor, "pk", "")) != str(owner):
            # A repuppeted session never renders the previous character's
            # fingerprint, cards, or degraded state (belt and braces).
            return None
    displayed = state.get("displayed")
    cards: tuple[FrozenCard, ...] | None = None
    if isinstance(displayed, (list, tuple)):
        cards = tuple(
            FrozenCard(
                kind=str(card.get("kind", "")),
                action_code=str(card.get("action_code", "")),
                label=str(card.get("label", "")),
                params=MappingProxyType(deepcopy(card.get("params") or {})),
                hint=card.get("hint"),
            )
            for card in displayed
            if isinstance(card, dict)
        )
    return OptionsSnapshot(
        fingerprint=state.get("fingerprint"),
        status=str(state.get("status", "")),
        generation_token=int(state.get("generation_token", 0)),
        displayed=cards,
    )


def proposal_snapshot(session: Any, actor: Any) -> ProposalSnapshot | None:
    """Return an immutable snapshot of ``session.ndb.concept_proposal``, or ``None``.

    The write side (the ``creation.concept`` adapter) populates the slot as a
    plain-data dict carrying ``owner_actor_id``, ``revision``, ``race``,
    ``subrace``, ``allocations``, and ``persona``; this read-side factory
    deep-copies the content into the frozen :class:`ProposalSnapshot` so a
    presenter's render is stable and never exposes a live reference. Mirrors
    :func:`options_snapshot`: an absent slot yields ``None``, a slot owned by
    a different actor is refused (the proposal never follows a puppet switch),
    and any malformed or incomplete shape degrades to ``None`` — this factory
    must never raise on the publication path (retool-concept-transient-fill
    D1).
    """
    ndb = getattr(session, "ndb", None)
    state = getattr(ndb, "concept_proposal", None) if ndb is not None else None
    if state is None:
        return None
    try:
        return _build_proposal_snapshot(actor, state)
    except Exception:
        log_unavailable("proposal snapshot", "malformed concept_proposal degraded to None")
        return None


def _build_proposal_snapshot(actor: Any, state: Any) -> ProposalSnapshot | None:
    if not isinstance(state, dict):
        return None
    owner = state.get("owner_actor_id")
    if owner is None or str(getattr(actor, "pk", "")) != str(owner):
        # An unowned slot (foreign actor or missing binding) never renders.
        return None
    revision = state.get("revision")
    race = state.get("race")
    subrace = state.get("subrace")
    allocations = state.get("allocations")
    persona = state.get("persona")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return None
    if not isinstance(race, str) or not race:
        return None
    if subrace is not None and (not isinstance(subrace, str) or not subrace):
        return None
    # The five optional transient-fill keys ride the gate only when present;
    # absent slots simply omit them. Presence is key existence: a null value
    # is corruption the exact contract rejects, never a silent absence
    # (bump-creation-panel-proposal-v3 D1).
    transient_fill: dict[str, Any] = {}
    for key in ("display_name", "age", "apparent_age", "background", "affinity_elements"):
        if key in state:
            transient_fill[key] = deepcopy(state[key])
    # A corrupt owned slot must degrade to an omitted proposal, never to an
    # unavailable panel: gate the content through the panel's own exact
    # proposal contract (seven axes, three persona keys, the 600-character
    # bound) so a half-valid dict can never reach ProposalSnapshot and blow up
    # the downstream creation validator (retool-concept-transient-fill D1).
    # Imported inside the function: the registry module graph reaches
    # creation.py, which reaches this module's registry import.
    from web.webclient.presentation.creation import _validate_proposal

    try:
        gate = {
            "revision": revision,
            "race": race,
            "subrace": subrace,
            "allocations": allocations,
            "persona": persona,
        }
        gate.update(transient_fill)
        _validate_proposal(gate)
    except Exception:
        return None
    return ProposalSnapshot(
        revision=revision,
        race=race,
        subrace=subrace,
        allocations=MappingProxyType(deepcopy(dict(allocations))),
        persona=MappingProxyType(deepcopy(dict(persona))),
        display_name=transient_fill.get("display_name"),
        age=transient_fill.get("age"),
        apparent_age=transient_fill.get("apparent_age"),
        background=transient_fill.get("background"),
        affinity_elements=(
            tuple(transient_fill["affinity_elements"])
            if "affinity_elements" in transient_fill
            else None
        ),
    )


def build_presentation_context(session: Any, actor: Any) -> PresentationContext:
    """The single factory every publication path builds its context through.

    Full-snapshot synchronization, the dispatcher's completion, internal-error,
    and stale paths, the art-completion push, and the trigger service's own
    guarded push all assemble their :class:`PresentationContext` through this
    factory, so no path can omit the options snapshot. It deep-copies
    ``session.ndb.options_state`` into the immutable :class:`OptionsSnapshot`
    (an absent or malformed state degrades to ``None``, and a snapshot whose
    owner differs from the rendering puppet is refused) and derives the
    current exploration situation fingerprint through the shared freshness
    derivation (``None`` when no situation can be derived — for example in
    combat, creation, or on a malformed actor — and never raising into the
    publication path). It never hands the raw session to a presenter.
    """
    return PresentationContext(
        actor=actor,
        protocol_version=PROTOCOL_VERSION,
        options_state=options_snapshot(session),
        options_fingerprint=_current_options_fingerprint(actor),
        proposal=proposal_snapshot(session, actor),
    )


def _current_options_fingerprint(actor: Any) -> str | None:
    """The current exploration situation fingerprint, or ``None``.

    Read-only and fail-closed: a derivation that cannot name the situation
    (or raises on a malformed actor) yields ``None`` so the suggestions
    presenter emits ``unavailable`` instead of rendering a stale snapshot.
    """
    try:
        from web.webclient.presentation.fingerprints import derive_exploration_situation

        situation = derive_exploration_situation(actor)
    except Exception:
        log_unavailable(
            "options fingerprint",
            "exploration situation derivation failed (degraded to None)",
        )
        return None
    return situation[0] if situation is not None else None


def synchronize_session(session: Any, actor: Any) -> bool:
    """Emit a full snapshot for a puppeted session; return success.

    Returns ``True`` after a snapshot is sent, ``False`` when a safe protocol
    error replaced it (for example, the world clock is unexpectedly absent).
    Never raises: presentation failures are logged and isolated so text play is
    unaffected.
    """
    coordinator = _coordinator_for(session, actor)
    context = build_presentation_context(session, actor)
    try:
        coordinator.synchronize(context)
    except ClockUnavailable:
        log_unavailable(coordinator.describe_session(), "world clock is absent")
        send_protocol_error(
            session,
            code="presentation_unavailable",
            message="目前無法取得世界時間，圖形介面暫停同步",
            reload_required=False,
        )
        return False
    except Exception:
        correlation_id = __import__("secrets").token_hex(16)
        log_unavailable(coordinator.describe_session(), f"sync failed {correlation_id}")
        send_protocol_error(
            session,
            code="internal_error",
            message="同步時發生內部錯誤",
            reload_required=True,
            correlation_id=correlation_id,
        )
        return False
    # The snapshot is on the wire; this session is a live watcher of its
    # puppet for the room-entry hook (idempotent per session). A function-local
    # import keeps the ingress importable while a worker is under development
    # and avoids a module cycle (watchers imports the ingress predicate).
    from web.webclient.presentation.watchers import register_watcher

    register_watcher(session)
    _schedule_on_reconnect(session, actor, coordinator)
    return True


def _schedule_on_reconnect(
    session: Any,
    actor: Any,
    coordinator: Any,
) -> None:
    """Fire-and-forget the action-options trigger after a successful sync.

    The requesting session is the sole watcher; whether a generation actually
    starts is decided by the service's stale predicate (absent options state,
    changed fingerprint, or a non-ready/non-cached state), never by this hook.
    Covers both ``ui_sync`` and post-command refresh with one seam. Fire-and-
    forget: any synchronous failure is logged and swallowed so the snapshot
    path is never altered.
    """
    try:
        from server.option_proposal_service import schedule_action_options

        schedule_action_options(actor, watchers=((session, coordinator.epoch),))
    except Exception:
        log_unavailable(
            getattr(session, "sessid", "?"),
            "reconnect trigger scheduling failed (swallowed)",
        )


def refresh_after_command(session: Any, actor: Any) -> None:
    """Best-effort full snapshot after a WebClient command settles.

    Presentation failure is logged separately and never replaces the command's
    own value or Failure; Telnet and AJAX sessions are never touched.
    """
    if not is_webclient(session):
        return
    try:
        synchronize_session(session, actor)
    except Exception:
        correlation_id = __import__("secrets").token_hex(16)
        log_unavailable(getattr(session, "sessid", "?"), f"refresh failed {correlation_id}")


def observe_command_settlement(deferred: Deferred, session: Any) -> None:
    """Attach a non-consuming observer to a command Deferred.

    ``deferred`` is the Deferred returned by Evennia's command handler. The
    observer runs once on either the callback or errback path, preserves the
    original success value or Failure unchanged, and then attempts one safe
    presentation refresh for WebClient sessions.
    """

    def _attempt(value: Any) -> Any:
        actor = getattr(session, "puppet", None)
        if actor is not None:
            refresh_after_command(session, actor)
        return value

    def _attempt_failure(failure: Any) -> Any:
        actor = getattr(session, "puppet", None)
        if actor is not None:
            try:
                refresh_after_command(session, actor)
            except Exception:
                correlation_id = __import__("secrets").token_hex(16)
                log_unavailable(getattr(session, "sessid", "?"), f"refresh failed {correlation_id}")
        return failure

    deferred.addCallbacks(_attempt, _attempt_failure)
