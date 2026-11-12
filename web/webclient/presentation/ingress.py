"""Server-side ingress and post-command refresh helpers for the OOB protocol.

These helpers isolate the Evennia session plumbing from the pure protocol and
coordinator modules: the input functions in ``server/conf/inputfuncs.py`` stay
thin and delegate authentication, synchronization, protocol-error emission, and
post-command refresh here.
"""

from copy import deepcopy
import secrets
from types import MappingProxyType
from typing import Any

from twisted.internet.defer import Deferred
from twisted.internet.defer import succeed
from twisted.python.failure import Failure

from web.webclient.presentation.context import (
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
    ProtocolValidationError,
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
        # A puppet change starts a distinct presentation sequence.
        coordinator.reset()
        # The transient concept proposal belongs to the old puppet: the new
        # puppet never sees it.
        session.ndb.concept_proposal = None
        session.ndb.skill_use_selection = None
        session.ndb.party_actor_selection = None
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
        session.ndb.concept_proposal = None
        session.ndb.skill_use_selection = None
        session.ndb.party_actor_selection = None


def proposal_snapshot(session: Any, actor: Any) -> ProposalSnapshot | None:
    """Return an immutable snapshot of ``session.ndb.concept_proposal``, or ``None``.

    The write side (the ``creation.concept`` adapter) populates the slot as a
    plain-data dict carrying ``owner_actor_id``, ``revision``, ``race``,
    ``subrace``, ``allocations``, and ``persona``; this read-side factory
    deep-copies the content into the frozen :class:`ProposalSnapshot` so a
    presenter's render is stable and never exposes a live reference. Mirrors
    the absent/malformed-slot contract: an absent slot yields ``None``, a slot
    owned by a different actor is refused (the proposal never follows a puppet
    switch), and any malformed or incomplete shape degrades to ``None`` — this
    factory must never raise on the publication path
    (retool-concept-transient-fill D1).
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


def build_presentation_context(
    session: Any, actor: Any, *, combat_round: Any = None
) -> PresentationContext:
    """The single factory every publication path builds its context through.

    Full-snapshot synchronization, the dispatcher's completion, internal-error,
    and stale paths, and the art-completion push all assemble their
    :class:`PresentationContext` through this factory, so no path can omit a
    session-scoped snapshot. It never hands the raw session to a presenter.

    ``combat_round`` is the completing combat action's frozen round record.
    Only the dispatcher's completion publication passes it (combat-beats-panel
    D2); every other caller leaves it ``None``, so the beats panel stays
    unavailable outside the one publication that settled the round.

    ``unlocks`` is the session's own unlock snapshot copied through
    :func:`world.rules.unlock_notices.unlock_flags`, so presenters read the
    unread dot and the recent set without touching ``ndb``.

    ``party_view`` is this session's viewed-member selection copied through
    ``party_view_selection_snapshot``: it survives possession, and a reconnect
    starts without one.

    ``gallery_view`` is the gallery view read by the registered (version-4)
    gallery presenter, copied through ``gallery_view_snapshot``; like ``party_view`` it is bound to the owning
    character and survives possession.
    """
    from web.webclient.presentation.gallery_selection import (
        gallery_selection_snapshot,
        gallery_view_snapshot,
    )
    from web.webclient.presentation.party_actor_selection import (
        party_actor_selection_snapshot,
    )
    from web.webclient.presentation.party_view_selection import (
        party_view_selection_snapshot,
    )
    from web.webclient.presentation.skill_use_selection import skill_use_selection_snapshot
    from world.rules.unlock_notices import unlock_flags

    return PresentationContext(
        actor=actor,
        protocol_version=PROTOCOL_VERSION,
        proposal=proposal_snapshot(session, actor),
        gallery_subject=gallery_selection_snapshot(session, actor),
        combat_round=combat_round,
        skill_use=skill_use_selection_snapshot(session, actor),
        party_actor=party_actor_selection_snapshot(session, actor),
        unlocks=unlock_flags(session),
        party_view=party_view_selection_snapshot(session, actor),
        gallery_view=gallery_view_snapshot(session, actor),
    )


def synchronize_session(session: Any, actor: Any) -> Deferred:
    """Publish the complete baseline for a puppeted session; return its Deferred.

    The publication is the coordinator's serialized own batch: the Deferred
    resolves with the actual :class:`PublicationReceipt` once every frame has
    sent and this helper has registered the watcher, or ``None`` when the
    sequence retired before it ran (nothing is registered then). A failure —
    the world clock absent, or any publication error — is reported through the
    safe protocol error and never raises into text play.

    An explicit synchronization is an independent queue entry: it never joins
    the causal group of a command that happens to be executing, so it cannot
    promote or answer for that command's presentation.
    """
    coordinator = _coordinator_for(session, actor)
    deferred = coordinator.enqueue_publication(
        lambda: build_presentation_context(session, actor),
        force_snapshot=True,
        independent=True,
    )

    def _published(receipt: Any) -> Any:
        if receipt is None:
            # The captured sequence retired before execution: this session is
            # no longer a watcher of ``actor``.
            return None
        # The snapshot is on the wire; this session is a live watcher of its
        # puppet for every targeted push (idempotent per session). A
        # function-local import keeps the ingress importable while a worker is
        # under development and avoids a module cycle (watchers imports the
        # ingress predicate).
        from web.webclient.presentation.watchers import register_watcher

        register_watcher(session)
        return receipt

    def _failed(failure: Failure) -> None:
        quiet = isinstance(failure, Failure) and failure.check(ClockUnavailable)
        # The complete snapshot itself violates the publication policy (an
        # over-limit or schema-invalid logical document). Retrying cannot fix
        # that, and nothing is ever truncated to fit: report the presentation
        # unavailable and stop, which is exactly the bounded failed repair.
        unpublishable = isinstance(failure, Failure) and failure.check(
            ProtocolValidationError
        )
        try:
            if quiet:
                log_unavailable(coordinator.describe_session(), "world clock is absent")
                send_protocol_error(
                    session,
                    code="presentation_unavailable",
                    message="目前無法取得世界時間，圖形介面暫停同步",
                    reload_required=False,
                )
                return None
            if unpublishable:
                log_unavailable(
                    coordinator.describe_session(),
                    "complete presentation exceeds the publication policy",
                )
                send_protocol_error(
                    session,
                    code="presentation_unavailable",
                    message="目前無法傳送完整的圖形介面資料，圖形介面暫停同步",
                    reload_required=False,
                )
                return None
            correlation_id = secrets.token_hex(16)
            log_unavailable(
                coordinator.describe_session(), f"sync failed {correlation_id}"
            )
            send_protocol_error(
                session,
                code="internal_error",
                message="同步時發生內部錯誤",
                reload_required=True,
                correlation_id=correlation_id,
            )
        except Exception as send_error:
            # A transport that cannot carry the safe protocol error is already
            # gone; the failure is reported here instead of raising into the
            # caller's command settlement.
            log_unavailable(
                coordinator.describe_session(),
                f"sync failure could not be reported ({type(send_error).__name__})",
            )
        return None

    deferred.addCallbacks(_published, _failed)
    return deferred


def refresh_after_command(session: Any, actor: Any) -> Deferred:
    """Best-effort comparison refresh after a WebClient command settles.

    The settled command's eager scope is unknown, so every eager panel is
    re-rendered from then-current canonical state and only real differences are
    transmitted: a command that changed nothing consumes no revision and sends
    no presentation frame. The returned Deferred carries the actual receipt (or
    ``None`` for a retired sequence); presentation failure is logged separately
    and never replaces the command's own value or Failure; Telnet and AJAX
    sessions are never touched.

    This refresh is its own queue entry, never a member of the command's causal
    group: the command's committed group has already published (or is about to
    at the reactor boundary), and a second current-state comparison is exactly
    what "the command settled" means. Two commands settling in reverse order
    therefore enqueue two refreshes in completion order, each against the
    then-current canonical state.
    """
    if not is_webclient(session):
        return succeed(None)
    coordinator = _coordinator_for(session, actor)
    deferred = coordinator.enqueue_publication(
        lambda: build_presentation_context(session, actor), independent=True
    )

    def _published(receipt: Any) -> Any:
        if receipt is None:
            return None
        from web.webclient.presentation.watchers import register_watcher

        register_watcher(session)
        return receipt

    def _failed(failure: Failure) -> None:
        error = failure.value if isinstance(failure, Failure) else failure
        correlation_id = secrets.token_hex(16)
        log_unavailable(
            getattr(session, "sessid", "?"),
            f"refresh failed {correlation_id} ({type(error).__name__})",
        )
        return None

    deferred.addCallbacks(_published, _failed)
    return deferred


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
