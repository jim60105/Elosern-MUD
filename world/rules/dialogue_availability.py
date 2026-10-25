"""One pure availability and disclosure projection for authored dialogue topics.

``project_topics`` is the single disclosure decision for a conversation. Given
the current canonical ``DialogueContext`` it answers which declared topics are
open, which stay visibly locked behind their authored refusal scene, and which
are absent: hidden topics simply never appear. Every consumer reads it -- the
version-3 dialogue panel, the exploration ``explore.talk_scripted`` vocabulary,
the deterministic selection boundary and the text ``talk`` surface -- so no
surface can disagree about a topic's availability or disclose a protected body
before the selection boundary authorizes it.

A projected row carries only disclosure-safe facts: the stable topic ID, the
authored keyword and label, the lock state, the canonical requirement hint
rendered from the SAME condition declaration the evaluator walks, and the
server-built action descriptor. It never carries a scene, a variant, a
fallback body, a successor bundle or any private source text. The authorized
scene (or the authored refusal) is chosen later, inside
``select_authored_topic``, which rechecks current canonical state before any
effect or delivery.

Disclosure rules, all fail-closed:

- a hidden topic is absent, and an explicit topic ID behaves exactly like an
  unknown one (no label, hint, body or chain structure leaks);
- a locked topic is disclosed only when the declaration authors both
  ``unavailable="locked"`` and a refusal scene; the row carries the canonical
  hint and selection plays that refusal with zero effects;
- ``requires`` qualification uses the shared evaluator;
- an unmet formal predecessor stays unavailable because reading persistence
  does not exist in this slice, so no predecessor can be verified;
- with no lawful actor (for example a host-only presentation read, or a forged
  possession control) a guarded topic is never evaluated -- it is withheld
  instead of being asserted available or locked, and no spurious condition
  integrity event is emitted;
- a locked row whose canonical hint cannot render is withheld rather than
  shipped with an unrenderable requirement text.

``refresh_dialogue_availability(owner, *, cause)`` is the complete explicit
refresh API for this slice. It re-resolves the owner's current acting body and
fans the freshly rendered ``dialogue`` panel out to that body's live watchers
AFTER the owning transaction commits, through the existing pusher discipline
(epoch-guarded, failure-isolated per watcher, never persisting anything). A
failed push recovers on the next canonical sync and never reverses a
successful commit.

Production mutation hooks call ``queue_dialogue_refresh(owners, *, cause)``:
the narrow deterministic companion of the single-owner API, which takes the
canonical owner objects a writer captured BEFORE its destructive membership or
control write, registers one commit callback for the deduplicated owner
identities, and re-resolves each owner row plus its currently valid actor/host
context inside that callback. A callback therefore never trusts pre-commit
eligibility, and a rolled-back outer transaction discards the callback
entirely. ``affected_dialogue_owners(entity, *, prior_owner=None)`` is the
owner-discovery half: the persistent player itself, a companion's lawful bound
owner plus its currently lawful possession owner, and any explicitly supplied
prior owner captured before a detach -- never an account-wide sibling
character. Neither helper creates a conversation, session or selection.

``session_bearing_dialogue_bodies``/``session_bearing_dialogue_owners`` serve
the sources that are not scoped to one changed entity: a world-time commit and
a generated phase transition must reach an idle owner whose live conversation
depends on the new clock period or phase. Their discovery is the stored
``dialogue_session`` Attribute itself -- the single truth of who is speaking --
validated through the same live-session reader every presenter uses, so no
presence, party or account heuristic can invent a conversation.

The canonical physical source matrix lived here by this slice (exact commit
hooks, owner capture and acceptance) is documented in
``docs/development/dialogue-panel-protocol.md``; the lifecycle slice extends
the same two helpers for quest, clock, companion-presence and control sources.
Command and presentation observers are NOT a substitute for those hooks: a
committed writer with no live session (Telnet, a scripted clock tick, an
offline character, or another actor's state change) never walks a command,
panel render or action path, so only the owning writer can schedule the
refresh. Reading-completion refresh (``cause="reading_completed"``) belongs to
``authored-dialogue-reading-server``. The only non-mutation cause is
``"open"`` from the successful open/selection path.

Unread observation (``authored-dialogue-unread-notices``): every committed
fan-out, before it pushes, observes the acting body's live authored
conversation through ``world.narrative.dialogue_reading.observe_availability``
(declared IDs of the current source/phase plus the currently open projection)
and, when that leaves a pending announcement, claims it with
``claim_unlock_batch`` under the owner lock. Only a claimed batch reaches
``push_dialogue_reading``, which wraps it separately for each current watcher.
The claim happens with or without a watcher, so no failure or disconnect can
replay it later, while the durable unread markers stay. Observation never runs
in a presenter and is skipped for a freeform-only host (no scene source).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from world.observability import log_info, log_warn

TOPIC_OPEN = "open"
TOPIC_LOCKED = "locked"
AVAILABILITY_VALUES = (TOPIC_OPEN, TOPIC_LOCKED)

MAX_TOPIC_ID_CHARS = 2048
MAX_CONTEXT_ID_CHARS = 64
MAX_CAUSE_CHARS = 64

AVAILABILITY_REFRESHED_EVENT = "dialogue_availability_refreshed"
AVAILABILITY_REFRESH_FAILED_EVENT = "dialogue_availability_refresh_failed"
UNLOCK_BATCH_CLAIMED_EVENT = "dialogue_unlock_batch_claimed"
UNLOCK_OBSERVATION_FAILED_EVENT = "dialogue_unlock_observation_failed"


@dataclass(frozen=True)
class TopicProjection:
    """One disclosed topic: identity, label, lock state, hint and descriptor.

    ``requirement_hint`` is the canonical player-facing requirement text and
    is non-null only for a locked row. ``descriptor`` is the exact
    ``explore.talk_scripted`` projection (``npc_id``/``topic_id``/``context_id``)
    the client echoes back; it carries no request identity and no content.
    ``unread`` marks an open formal topic this owner has not completed yet
    (a locked row is never unread: the lock marker takes precedence), and
    ``predecessors`` is the declared public-chain gate list.
    """

    topic_id: str
    keyword: str
    label: str
    availability: str
    requirement_hint: str | None
    descriptor: dict[str, Any]
    unread: bool
    predecessors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.topic_id, str) or not self.topic_id:
            raise ValueError("topic_id must be a non-empty string")
        if not isinstance(self.keyword, str) or not self.keyword:
            raise ValueError("keyword must be a non-empty string")
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("label must be a non-empty string")
        if self.availability not in AVAILABILITY_VALUES:
            raise ValueError(f"availability must be open or locked, got {self.availability!r}")
        if self.requirement_hint is not None and not isinstance(self.requirement_hint, str):
            raise ValueError("requirement_hint must be a str or None")
        if not isinstance(self.descriptor, dict):
            raise ValueError("descriptor must be an object")
        if not isinstance(self.unread, bool):
            raise ValueError("unread must be a boolean")
        if not isinstance(self.predecessors, tuple) or any(
            not isinstance(item, str) or not item for item in self.predecessors
        ):
            raise ValueError("predecessors must be a tuple of non-empty strings")


def availability_context(actor: Any, host: Any) -> Any:
    """The projection context of ``actor`` at ``host``, degrading to host-only.

    A lawful actor resolves through the canonical context reader. Anything else
    (a non-lawful possession control, a remote or self host, a host-only
    presentation read) degrades to a host-only context whose missing actor
    withholds every guarded topic: presentation may enumerate an
    unconditional topic for a disabled row, but it never asserts that a
    conditional one is available or locked.
    """
    from world.rules.dialogue_context import (
        DialogueContext,
        DialogueContextError,
        host_dialogue_binding,
        resolve_dialogue_context,
    )

    if actor is not None:
        try:
            return resolve_dialogue_context(actor, host)
        except DialogueContextError:  # observability: ignore R2: a non-lawful actor degrades to host-only disclosure, never an availability assertion
            pass
    host_key, source_identity = host_dialogue_binding(host)
    return DialogueContext(
        actor=None,
        owner=None,
        host=host,
        host_key=host_key,
        source_identity=source_identity,
        context_id=None,
        phase_revision=None,
    )


def project_topics(
    context: Any, *, context_id: str | None = None
) -> tuple[TopicProjection, ...]:
    """Project the currently disclosed topics of ``context``'s dialogue source.

    Declaration order is preserved. ``context_id`` stamps the action
    descriptor with the context the caller will publish (a live session's
    context, or the context a direct selection is about to establish); the
    prompt never comes from the client. The owner's saved reading is read once
    per projection and gates every predecessor: a public successor appears only
    after its predecessors are saved, and an open formal topic the owner has not
    completed yet is marked unread.
    """
    from world.rules.dialogue_sources import resolve_dialogue_source

    if context_id is not None and (
        not isinstance(context_id, str) or len(context_id) > MAX_CONTEXT_ID_CHARS
    ):
        raise ValueError(
            f"context_id must be a str <= {MAX_CONTEXT_ID_CHARS} characters or None"
        )
    source = resolve_dialogue_source(context)
    if source is None:
        return ()
    npc_id = int(getattr(getattr(context, "host", None), "pk", 0) or 0)
    if npc_id <= 0:
        return ()
    completed = _completed_reading(context)

    rows: list[TopicProjection] = []
    for topic in source.dialogue.topics:
        disclosure = _disclosure(topic, context, completed)
        if disclosure is None:
            continue
        availability, hint = disclosure
        topic_id = topic.topic_id
        rows.append(
            TopicProjection(
                topic_id=topic_id,
                keyword=topic.keyword,
                label=topic.label,
                availability=availability,
                requirement_hint=hint,
                descriptor={
                    "npc_id": npc_id,
                    "topic_id": topic_id,
                    "context_id": context_id,
                },
                unread=availability == TOPIC_OPEN and topic_id not in completed,
                predecessors=tuple(getattr(topic, "predecessors", ()) or ()),
            )
        )
    return tuple(rows)


def _completed_reading(context: Any) -> frozenset[str]:
    """The owner's saved completions at this host, or an empty set. Read-only."""
    owner = getattr(context, "owner", None)
    host_key = getattr(context, "host_key", None)
    if owner is None or not host_key:
        return frozenset()
    from world.narrative.dialogue_reading import completed_topic_ids

    return frozenset(completed_topic_ids(owner, host_key))


def _disclosure(
    topic: Any, context: Any, completed: frozenset[str] | set[str]
) -> tuple[str, str | None] | None:
    """Classify one topic: ``(availability, hint)``, or ``None`` when hidden.

    Predecessors are served by saved reading. An unmet predecessor withholds
    the topic entirely — even one declared ``unavailable="locked"`` — because a
    public successor must not be revealed before its predecessor is read and a
    protected qualified descendant must never advertise itself early. A failed
    ``requires`` keeps the existing locked/hidden declaration behavior.
    """
    from world.rules.dialogue_conditions import (
        DialogueConditionError,
        condition_hint,
        evaluate_condition,
    )

    requires = getattr(topic, "requires", None)
    predecessors = tuple(getattr(topic, "predecessors", ()) or ())
    if (requires is not None or predecessors) and getattr(context, "actor", None) is None:
        # No lawful actor: evaluating would emit a spurious integrity event and
        # could only guess, so the guarded topic is withheld.
        return None
    if any(predecessor not in completed for predecessor in predecessors):
        return None
    if requires is None or evaluate_condition(requires, context):
        return (TOPIC_OPEN, None)

    # A failed ``requires`` is unqualified: it fails closed.
    if getattr(topic, "unavailable", "hidden") != "locked":
        return None
    if getattr(topic, "refusal", None) is None:
        return None
    try:
        hint = condition_hint(requires, context) if requires is not None else None
    except DialogueConditionError:  # observability: ignore R2: an unrenderable locked hint withholds the row instead of disclosing it
        return None
    return (TOPIC_LOCKED, hint)


def refresh_dialogue_availability(owner: Any, *, cause: str) -> None:
    """Re-resolve the owner's current conversation and fan the panel out.

    The fan-out is registered on the owning transaction's commit hook, so a
    rolled-back write fans out nothing and a committed write never reports a
    presentation failure as a gameplay failure. The acting body (the owner, or
    the companion it lawfully possesses) is resolved inside that callback, so a
    control change between scheduling and commit refreshes the body that is
    actually acting.
    """
    if not isinstance(cause, str) or not cause or len(cause) > MAX_CAUSE_CHARS:
        raise ValueError(
            f"cause must be a non-empty string <= {MAX_CAUSE_CHARS} characters"
        )
    from django.db import transaction

    transaction.on_commit(lambda: _fan_out_availability(owner, cause))


def queue_dialogue_refresh(owners: Iterable[Any], *, cause: str) -> None:
    """Schedule one committed availability refresh for explicit owner objects.

    The narrow deterministic helper the canonical physical writers call AFTER
    their validated write. ``owners`` are owner entities the caller captured
    before any destructive membership or control write; non-owner entries and
    duplicates are dropped, so a writer can hand the raw helper output over.

    The fan-out is registered on the owning transaction's commit hook. Inside
    an outer transaction the callback runs only after that transaction
    commits, so a late rollback discards it and no false eligibility or
    reading mutation is ever published; outside an atomic block it runs after
    the successful owning write. Each callback re-resolves the owner row from
    its identity and then re-resolves its currently valid acting body and
    conversation from committed state -- the pre-commit objects and their
    pre-commit eligibility are never reused for projection or push. Several
    callbacks from one outer operation may therefore all run; every one of
    them evaluates the final committed state.

    This helper never creates a conversation, a dialogue session or a
    selection, and never touches an authored package.
    """
    if not isinstance(cause, str) or not cause or len(cause) > MAX_CAUSE_CHARS:
        raise ValueError(
            f"cause must be a non-empty string <= {MAX_CAUSE_CHARS} characters"
        )
    owner_ids = _owner_ids(owners)
    if not owner_ids:
        return
    from django.db import transaction

    transaction.on_commit(lambda: _fan_out_owner_ids(owner_ids, cause))


def affected_dialogue_owners(
    entity: Any, *, prior_owner: Any = None
) -> tuple[Any, ...]:
    """The dialogue owners whose availability ``entity``'s change can affect.

    A persistent player owns itself. Any other changed actor (a companion or
    any other NPC-shaped body) contributes its lawful bound party owner and
    its currently lawful possession owner, resolved by reading the same
    bidirectional bindings the dialogue authority boundary reads. A caller
    that is about to detach a body captures the owner BEFORE the destructive
    write and passes it as ``prior_owner``, so the owner that loses the body
    still receives one refresh once the new committed state is visible.

    Only lawful owner identities are returned: no account-wide sibling
    character, no stale or one-sided binding, and no forged possession mirror.
    The result is deduplicated in capture order and may be empty (an
    unowned/NPC body, or construction that has no live conversation). This
    helper only reads; it never creates a conversation, session or selection.
    """
    candidates: list[Any] = []
    if _owner_identity(entity) is not None:
        candidates.append(entity)
    else:
        from world.rules.party import bound_owner_of

        candidates.append(bound_owner_of(entity) if entity is not None else None)
        candidates.append(_possession_owner(entity))
    candidates.append(prior_owner)
    return _unique_owners(candidates)


def session_bearing_dialogue_bodies() -> tuple[Any, ...]:
    """Every persistent body that currently holds one live authored session.

    World-time and phase commits are not scoped to an action's entities: an
    idle player in another room may still be talking to a host whose
    eligibility depends on the new clock period or phase. The stored
    ``dialogue_session`` Attribute is the discovery key (the single truth of
    who is speaking), and each candidate is validated through the canonical
    live-session reader, so a corrupt value, a departed host or a stale
    control identity is skipped exactly as every presenter skips it.

    Read-only and never raising: discovery is best-effort scheduling after a
    successful owning write, so an unreadable candidate body is skipped
    instead of failing the commit. Never creates a conversation or selection.
    """
    from evennia.objects.models import ObjectDB

    from world.rules.dialogue import live_dialogue_session

    try:
        through = ObjectDB.db_attributes.through
        body_ids = tuple(
            dict.fromkeys(
                through.objects.filter(attribute__db_key="dialogue_session")
                .values_list("objectdb_id", flat=True)
            )
        )
        if not body_ids:
            return ()
        rows = tuple(ObjectDB.objects.filter(id__in=body_ids))
    except Exception:  # observability: ignore R2: discovery only schedules presentation for a write that already committed; the next canonical sync recovers, so a query failure must never fail the writer
        return ()
    bodies: list[Any] = []
    for body in rows:
        try:
            if live_dialogue_session(body) is None:
                continue
        except Exception:  # observability: ignore R2: one unreadable body is skipped; another owner's refresh must still run and the commit must stand
            continue
        bodies.append(body)
    return tuple(bodies)


def session_bearing_dialogue_owners() -> tuple[Any, ...]:
    """The lawful owners of every live session-bearing body, deduplicated.

    The owner half of the world-time/phase discovery above: a player body owns
    itself, while a possessed companion resolves through the same lawful
    binding and possession checks as ``affected_dialogue_owners``. An
    account-wide sibling never appears. Read-only; never creates state.
    """
    candidates: list[Any] = []
    for body in session_bearing_dialogue_bodies():
        candidates.extend(affected_dialogue_owners(body))
    return _unique_owners(candidates)


def _owner_identity(entity: Any) -> int | None:
    """The persistent pk of one legitimate dialogue owner, or ``None``."""
    from typeclasses.characters import PlayerCharacter

    if not isinstance(entity, PlayerCharacter):
        return None
    pk = getattr(entity, "pk", None)
    if isinstance(pk, bool) or not isinstance(pk, int) or pk <= 0:
        return None
    return pk


def _possession_owner(body: Any) -> Any:
    """The player lawfully possessing ``body`` right now, or ``None``.

    Both directions of the stored possession mirror must agree AND the body
    must still be bound to that player through the canonical party binding, so
    a body whose party binding was removed (or whose possession mirror was
    forged) resolves no possession owner even while the mirror references
    still agree. The bound party owner remains the separate owner category.
    """
    holder = getattr(getattr(body, "db", None), "possessed_by", None)
    if isinstance(holder, bool) or not isinstance(holder, int) or holder <= 0:
        return None
    from evennia.objects.objects import ObjectDB

    from world.rules.party import bound_owner_of
    from world.rules.possession import current_possession

    player = ObjectDB.objects.filter(id=holder).first()
    if _owner_identity(player) is None:
        return None
    if bound_owner_of(body) is not player:
        return None
    binding = current_possession(player)
    if binding is None or binding["npc_dbid"] != int(getattr(body, "pk", 0) or 0):
        return None
    return player


def _unique_owners(candidates: Iterable[Any]) -> tuple[Any, ...]:
    """Filter to lawful owners and deduplicate them by persistent identity."""
    owners: list[Any] = []
    seen: set[int] = set()
    for candidate in candidates:
        identity = _owner_identity(candidate)
        if identity is None or identity in seen:
            continue
        seen.add(identity)
        owners.append(candidate)
    return tuple(owners)


def _owner_ids(owners: Iterable[Any]) -> tuple[int, ...]:
    """The deduplicated persistent identities of an explicit owner iterable."""
    if isinstance(owners, (str, bytes)) or not isinstance(owners, Iterable):
        raise TypeError("owners must be an iterable of dialogue owner entities")
    return tuple(
        identity
        for identity in map(_owner_identity, owners)
        if identity is not None
    )


def _fan_out_owner_ids(owner_ids: tuple[int, ...], cause: str) -> None:
    """Post-commit fan-out over re-resolved owner rows (never raises)."""
    from evennia.objects.objects import ObjectDB

    for owner_id in owner_ids:
        try:
            owner = ObjectDB.objects.filter(id=owner_id).first()
        except Exception as error:
            log_warn(
                AVAILABILITY_REFRESH_FAILED_EVENT,
                context={"char": str(owner_id), "cause": cause},
                exc=error,
            )
            continue
        if owner is None:
            # A deleted owner has nothing to present; the next canonical sync
            # of its surviving watchers owns that transition.
            continue
        _fan_out_availability(owner, cause)


def _fan_out_availability(owner: Any, cause: str) -> None:
    """Post-commit current-state projection and panel fan-out (never raises)."""
    owner_id = str(getattr(owner, "pk", "?"))
    try:
        from web.webclient.presentation.dialogue_push import push_dialogue_reading
        from world.rules.dialogue import live_dialogue_session

        body = _acting_body(owner)
        session = live_dialogue_session(body)
        log_info(
            AVAILABILITY_REFRESHED_EVENT,
            context={
                "char": owner_id,
                "actor": str(getattr(body, "pk", "?")),
                "npc": str(session.npc_id) if session is not None else "?",
                "context": str(session.context_id) if session is not None else "?",
                "cause": cause,
            },
        )
        claimed = (
            _observe_unlocks(owner, body, session, cause)
            if session is not None
            else None
        )
        # Every CURRENT connection of the owning player receives its OWN
        # re-rendered panel: another character of the same account is excluded
        # and no connection's locally playing scene is replaced. A claimed
        # unlock batch rides only this live push, never a snapshot.
        if claimed is None:
            push_dialogue_reading(owner)
        else:
            push_dialogue_reading(owner, unlock_batch=claimed)
    except Exception as error:
        log_warn(
            AVAILABILITY_REFRESH_FAILED_EVENT,
            context={"char": owner_id, "cause": cause},
            exc=error,
        )


def _observe_unlocks(owner: Any, body: Any, session: Any, cause: str) -> Any:
    """Observe the live conversation and claim its pending batch, or ``None``.

    Failure-isolated: an observation or claim failure is reported once and the
    refresh still pushes the current panel (its unread markers are derived
    from saved reading, never from this observation).
    """
    from evennia.objects.objects import ObjectDB

    from world.narrative.dialogue_reading import (
        claim_unlock_batch,
        observe_availability,
    )
    from world.rules.dialogue_context import (
        DialogueContextError,
        resolve_dialogue_context,
    )
    from world.rules.dialogue_sources import resolve_dialogue_source

    owner_id = str(getattr(owner, "pk", "?"))
    try:
        host = ObjectDB.objects.filter(id=session.npc_id).first()
        if host is None:
            return None
        try:
            context = resolve_dialogue_context(body, host)
        except DialogueContextError:  # observability: ignore R2: a non-lawful context observes nothing; the push degrades on its own
            return None
        if context.owner is None or not context.host_key:
            return None
        if int(getattr(context.owner, "pk", 0) or 0) != int(getattr(owner, "pk", 0) or 0):
            # The reading row and the recipients must belong to one player:
            # never observe or claim for an owner whose watchers differ.
            log_warn(
                UNLOCK_OBSERVATION_FAILED_EVENT,
                context={
                    "char": owner_id,
                    "cause": cause,
                    "reason": "owner_mismatch",
                    "owner": str(getattr(context.owner, "pk", "?")),
                },
            )
            return None
        source = resolve_dialogue_source(context)
        if source is None:
            # A freeform-only host has no scene topics to observe.
            return None
        topics = tuple(source.dialogue.topics)
        declared = tuple(topic.topic_id for topic in topics)
        open_ids = tuple(
            row.topic_id
            for row in project_topics(context, context_id=session.context_id)
            if row.availability == TOPIC_OPEN
        )
        # A public chain successor gated only by its predecessors opens by
        # being read, not by a state change: no unlock notice for it.
        quiet = tuple(
            topic.topic_id
            for topic in topics
            if getattr(topic, "disclosure", "qualified") == "pure_chain"
            and getattr(topic, "requires", None) is None
        )
        pending = observe_availability(
            context.owner,
            context.host_key,
            open_ids,
            declared_topic_ids=declared,
            initial=cause == "open",
            context_id=session.context_id,
            quiet_topic_ids=quiet,
        )
        if pending is None:
            return None
        claimed = claim_unlock_batch(context.owner, pending.batch_id)
        if claimed is None:
            return None
        log_info(
            UNLOCK_BATCH_CLAIMED_EVENT,
            context={
                "char": owner_id,
                "actor": str(getattr(body, "pk", "?")),
                "npc": str(session.npc_id),
                "host": claimed.host_key,
                "batch": claimed.batch_id,
                "topics": len(claimed.topic_ids),
                "context": str(session.context_id),
                "cause": cause,
            },
        )
        return claimed
    except Exception as error:
        log_warn(
            UNLOCK_OBSERVATION_FAILED_EVENT,
            context={"char": owner_id, "cause": cause},
            exc=error,
        )
        return None


def _acting_body(owner: Any) -> Any:
    """The body currently acting for ``owner``: its possessed companion or itself.

    The stored possession mirror is only a locator: the companion must still
    name ``owner`` as its possessor AND remain bound to that owner through the
    canonical party binding, so a possession whose binding was removed between
    scheduling and this callback never receives the owner's refresh instead.
    """
    from evennia.objects.objects import ObjectDB

    from world.rules.party import bound_owner_of
    from world.rules.possession import current_possession

    possession = current_possession(owner)
    if possession is None:
        return owner
    body = ObjectDB.objects.filter(id=possession["npc_dbid"]).first()
    if body is None:
        return owner
    if getattr(getattr(body, "db", None), "possessed_by", None) != int(
        getattr(owner, "pk", 0)
    ):
        return owner
    if bound_owner_of(body) is not owner:
        return owner
    return body


__all__ = [
    "AVAILABILITY_VALUES",
    "MAX_CAUSE_CHARS",
    "MAX_CONTEXT_ID_CHARS",
    "MAX_TOPIC_ID_CHARS",
    "TOPIC_LOCKED",
    "TOPIC_OPEN",
    "UNLOCK_BATCH_CLAIMED_EVENT",
    "TopicProjection",
    "affected_dialogue_owners",
    "availability_context",
    "project_topics",
    "queue_dialogue_refresh",
    "refresh_dialogue_availability",
    "session_bearing_dialogue_bodies",
    "session_bearing_dialogue_owners",
]
