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

The canonical physical source matrix lived here by this slice (exact commit
hooks, owner capture and acceptance) is documented in
``docs/development/dialogue-panel-protocol.md``; the lifecycle slice extends
the same two helpers for quest, clock, companion-presence and control sources.
Command and presentation observers are NOT a substitute for those hooks: a
committed writer with no live session (Telnet, a scripted clock tick, an
offline character, or another actor's state change) never walks a command,
panel render or action path, so only the owning writer can schedule the
refresh. Reading-completion refresh (``cause="reading_completed"``) belongs to
``authored-dialogue-reading-server``; narrative first-observation and unlock
batches belong to ``authored-dialogue-unread-notices``, which extends this
callable with ``observe_availability``/``initial``. The only non-mutation cause
this slice adds is ``"open"`` from the successful open/selection path.
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


@dataclass(frozen=True)
class TopicProjection:
    """One disclosed topic: identity, label, lock state, hint and descriptor.

    ``requirement_hint`` is the canonical player-facing requirement text and
    is non-null only for a locked row. ``descriptor`` is the exact
    ``explore.talk_scripted`` projection (``npc_id``/``topic_id``/``context_id``)
    the client echoes back; it carries no request identity and no content.
    """

    topic_id: str
    keyword: str
    label: str
    availability: str
    requirement_hint: str | None
    descriptor: dict[str, Any]

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
    prompt never comes from the client.
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

    rows: list[TopicProjection] = []
    for topic in source.dialogue.topics:
        disclosure = _disclosure(topic, context)
        if disclosure is None:
            continue
        availability, hint = disclosure
        rows.append(
            TopicProjection(
                topic_id=topic.topic_id,
                keyword=topic.keyword,
                label=topic.label,
                availability=availability,
                requirement_hint=hint,
                descriptor={
                    "npc_id": npc_id,
                    "topic_id": topic.topic_id,
                    "context_id": context_id,
                },
            )
        )
    return tuple(rows)


def _disclosure(topic: Any, context: Any) -> tuple[str, str | None] | None:
    """Classify one topic: ``(availability, hint)``, or ``None`` when hidden."""
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
    if not predecessors and (requires is None or evaluate_condition(requires, context)):
        return (TOPIC_OPEN, None)

    # An unmet predecessor cannot be verified before reading persistence lands,
    # and a failed ``requires`` is unqualified: both fail closed.
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

    Both directions must hold: the body names the player as its possessor and
    the player's own possession binding names this body. A one-sided or
    forged mirror resolves no owner.
    """
    holder = getattr(getattr(body, "db", None), "possessed_by", None)
    if isinstance(holder, bool) or not isinstance(holder, int) or holder <= 0:
        return None
    from evennia.objects.objects import ObjectDB

    player = ObjectDB.objects.filter(id=holder).first()
    if _owner_identity(player) is None:
        return None
    from world.rules.possession import current_possession

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
        from web.webclient.presentation.dialogue_push import push_dialogue_update
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
        push_dialogue_update(body)
    except Exception as error:
        log_warn(
            AVAILABILITY_REFRESH_FAILED_EVENT,
            context={"char": owner_id, "cause": cause},
            exc=error,
        )


def _acting_body(owner: Any) -> Any:
    """The body currently acting for ``owner``: its possessed companion or itself."""
    from evennia.objects.objects import ObjectDB

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
    return body


__all__ = [
    "AVAILABILITY_VALUES",
    "MAX_CAUSE_CHARS",
    "MAX_CONTEXT_ID_CHARS",
    "MAX_TOPIC_ID_CHARS",
    "TOPIC_LOCKED",
    "TOPIC_OPEN",
    "TopicProjection",
    "affected_dialogue_owners",
    "availability_context",
    "project_topics",
    "queue_dialogue_refresh",
    "refresh_dialogue_availability",
]
