"""Deterministic story thread lifecycle and real cross-channel linkage.

Threads retain an immutable origin, participants, a factual summary, unresolved
questions, proposed plans, gameplay-established commitments, memory references,
and development ticks. Lifecycle states are explicit and deterministic:
inactivity may inform dormancy but never infers abandonment, and a quest
completion never resolves its parent thread. Every effective change appends a
``StoryThreadRevision`` row and advances the thread revision that retrieval and
context snapshots read.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from django.db import IntegrityError, transaction

from world.narrative.memory import revise_memory
from world.narrative.models import (
    DialogueTurn,
    LetterSend,
    MemoryRecord,
    NarrativeEvent,
    StoryThread,
    StoryThreadLink,
    StoryThreadRevision,
)
from world.observability import log_info

VALID_THREAD_STATES = frozenset({"active", "dormant", "resolved", "abandoned"})
# Explicit terminal states: no operation transitions a thread out of them.
TERMINAL_THREAD_STATES = frozenset({"resolved", "abandoned"})

THREAD_SOURCE_KINDS = ("event", "memory", "letter", "dialogue", "quest")

# Relation vocabulary is fixed per source kind so a caller cannot pre-create a
# completion/memory-reference link and turn a lifecycle operation into a no-op.
ALLOWED_RELATIONS_BY_KIND: dict[str, frozenset[str]] = {
    "event": frozenset({"origin", "development", "commitment"}),
    "memory": frozenset({"origin", "development", "memory_reference"}),
    "letter": frozenset({"origin", "development", "statement"}),
    "dialogue": frozenset({"origin", "development", "statement"}),
    "quest": frozenset({"origin", "development", "quest_completion"}),
}

# Statement channels: these narrative event types carry speech or claims and can
# never establish a gameplay commitment. Gameplay commit events (for example the
# existing encounter-protection commit) stay eligible.
NON_COMMITMENT_EVENT_TYPES = frozenset(
    {
        "claim_receipt",
        "correspondence_delivery",
        "correspondence_read",
        "private_authoring",
    }
)

MAX_THREAD_ID_LENGTH = 128


class NarrativeThreadError(Exception):
    """Base exception for story thread errors."""


class NarrativeThreadAccessError(NarrativeThreadError):
    """Raised when an actor is not permitted to read or link a thread."""


class NarrativeThreadStateError(NarrativeThreadError):
    """Raised when a lifecycle transition is invalid or unspecified."""


class NarrativeThreadSourceError(NarrativeThreadError):
    """Raised when a linked source is unknown or its shape is not permitted."""


class NarrativeThreadCommitmentError(NarrativeThreadError):
    """Raised when a commitment is attempted from a non-commitment source."""


def _clean_thread_id(thread_id: Any) -> str:
    """Canonical thread identity: one normalization for every comparison site."""
    clean = str(thread_id).strip()
    if not clean or len(clean) > MAX_THREAD_ID_LENGTH:
        raise NarrativeThreadError(
            f"thread_id must contain 1..{MAX_THREAD_ID_LENGTH} characters."
        )
    return clean


def memory_source_ref(record: Any) -> str:
    """Canonical durable reference for a memory record."""
    return f"mem:{int(record.pk)}"


def dialogue_source_ref(turn: Any) -> str:
    """Canonical durable reference for a preserved dialogue turn."""
    return f"{turn.submission_id}:{turn.kind}"


def get_thread(thread_id: Any) -> Optional[StoryThread]:
    """Return the thread with this identity, or None when it does not exist."""
    return StoryThread.objects.filter(thread_id=_clean_thread_id(thread_id)).first()


def _thread_id_or_none(thread_id: Any) -> Optional[str]:
    """Tolerant form of :func:`_clean_thread_id` for read-only lookups."""
    clean = str(thread_id).strip()
    if not clean or len(clean) > MAX_THREAD_ID_LENGTH:
        return None
    return clean


def find_thread(thread_id: Any) -> Optional[StoryThread]:
    """Tolerant lookup: the thread, or None when it is absent or malformed."""
    clean = _thread_id_or_none(thread_id)
    if clean is None:
        return None
    return StoryThread.objects.filter(thread_id=clean).first()


def get_thread_revision(thread_id: Any) -> int:
    """Current revision read identity for a thread; 0 when absent or malformed."""
    thread = find_thread(thread_id)
    return int(thread.revision) if thread is not None else 0


def thread_accessible(thread: Optional[StoryThread], owner_id: Any) -> bool:
    """Owner permissions constrain eligible thread membership before ranking."""
    if thread is None:
        return False
    owner = str(owner_id).strip()
    return any(str(item).strip() == owner for item in (thread.visible_to or []))


def _locked_thread(thread_id: Any) -> StoryThread:
    clean_id = _clean_thread_id(thread_id)
    thread = StoryThread.objects.select_for_update().filter(thread_id=clean_id).first()
    if thread is None:
        raise NarrativeThreadSourceError(f"Unknown story thread {clean_id!r}.")
    return thread


def _require_access(thread: StoryThread, actor_id: Optional[str]) -> None:
    if actor_id is None:
        return
    if not thread_accessible(thread, actor_id):
        raise NarrativeThreadAccessError(
            f"Actor {actor_id!r} cannot access story thread {thread.thread_id!r}."
        )


def _source_exists(source_kind: str, source_ref: str) -> bool:
    """Verify a durable source row exists in the channel that owns it."""
    if source_kind == "event":
        return NarrativeEvent.objects.filter(source_id=source_ref).exists()
    if source_kind == "letter":
        return LetterSend.objects.filter(source_id=source_ref).exists()
    if source_kind == "memory":
        prefix, _, pk = source_ref.partition(":")
        return prefix == "mem" and pk.isdigit() and MemoryRecord.objects.filter(pk=int(pk)).exists()
    if source_kind == "dialogue":
        submission_id, separator, kind = source_ref.rpartition(":")
        return bool(separator and submission_id) and DialogueTurn.objects.filter(
            submission_id=submission_id, kind=kind
        ).exists()
    if source_kind == "quest":
        # world/quests owns the quest lifecycle; narrative stores only the durable
        # quest identity and never duplicates or queries quest state.
        return True
    return False


def _validate_link_shape(source_kind: str, source_ref: str, relation: str) -> tuple[str, str, str]:
    clean_kind = str(source_kind).strip()
    if clean_kind not in THREAD_SOURCE_KINDS:
        raise NarrativeThreadSourceError(
            f"source_kind {clean_kind!r} must be one of {list(THREAD_SOURCE_KINDS)}."
        )
    clean_ref = str(source_ref).strip()
    if not clean_ref or len(clean_ref) > 255:
        raise NarrativeThreadSourceError("source_ref must contain 1..255 characters.")
    clean_relation = str(relation).strip()
    if clean_relation not in ALLOWED_RELATIONS_BY_KIND[clean_kind]:
        raise NarrativeThreadSourceError(
            f"relation {clean_relation!r} is not valid for {clean_kind!r} sources."
        )
    return clean_kind, clean_ref, clean_relation


def _create_link(
    thread: StoryThread,
    source_kind: str,
    source_ref: str,
    relation: str,
    provenance: Optional[dict[str, Any]],
    tick: int,
) -> tuple[StoryThreadLink, bool]:
    """Idempotent link creation; callers own the revision bump and the log."""
    link, created = StoryThreadLink.objects.get_or_create(
        thread=thread,
        source_kind=source_kind,
        source_ref=source_ref,
        relation=relation,
        defaults={"provenance": dict(provenance or {}), "created_tick": int(tick)},
    )
    return link, created


def _record_revision(
    thread: StoryThread,
    *,
    operation: str,
    details: Optional[dict[str, Any]] = None,
    changed_fields: Optional[Iterable[str]] = None,
) -> int:
    """Persist changed thread fields together with an append-only revision row."""
    revision = int(thread.revision) + 1
    thread.revision = revision
    update_fields = sorted(set(changed_fields or ()) | {"revision", "updated_at"})
    thread.save(update_fields=update_fields)
    StoryThreadRevision.objects.create(
        thread=thread,
        revision_number=revision,
        operation=operation,
        state=thread.state,
        details=dict(details or {}),
    )
    return revision


def _announce(event: str, boundary: dict[str, Any]) -> None:
    transaction.on_commit(lambda b=boundary: log_info(event, context=b))


def create_thread(
    *,
    thread_id: str,
    origin: str,
    participants: Iterable[str],
    visible_to: Optional[Iterable[str]] = None,
    tick: int = 0,
    factual_summary: str = "",
    unresolved_questions: Optional[Iterable[str]] = None,
    proposed_plans: Optional[Iterable[str]] = None,
) -> StoryThread:
    """Create an active thread with an immutable origin and revision 1.

    ``commitments`` only ever starts empty: only gameplay commits establish one.
    """
    clean_id = _clean_thread_id(thread_id)
    clean_origin = str(origin).strip()
    if not clean_origin:
        raise NarrativeThreadError("origin must be a durable reference.")
    clean_participants = [str(p).strip() for p in (participants or [])]
    if not clean_participants:
        raise NarrativeThreadError("participants must name at least one owner.")
    clean_visible = [
        str(o).strip()
        for o in (visible_to if visible_to is not None else clean_participants)
    ]

    with transaction.atomic():
        if StoryThread.objects.filter(thread_id=clean_id).exists():
            raise NarrativeThreadError(f"Story thread {clean_id!r} already exists.")
        try:
            with transaction.atomic():
                thread = StoryThread.objects.create(
                    thread_id=clean_id,
                    origin=clean_origin,
                    participants=clean_participants,
                    visible_to=clean_visible,
                    factual_summary=str(factual_summary or ""),
                    unresolved_questions=[str(q) for q in (unresolved_questions or [])],
                    proposed_plans=[str(p) for p in (proposed_plans or [])],
                    commitments=[],
                    memory_references=[],
                    development_ticks=[int(tick)],
                    state="active",
                    revision=1,
                    created_tick=int(tick),
                )
        except IntegrityError as exc:
            raise NarrativeThreadError(f"Story thread {clean_id!r} already exists.") from exc
        StoryThreadRevision.objects.create(
            thread=thread,
            revision_number=1,
            operation="created",
            state="active",
            details={"origin": clean_origin, "participants": clean_participants},
        )
        _announce(
            "narrative_thread_created",
            {
                "thread_id": clean_id,
                "origin": clean_origin,
                "participants": len(clean_participants),
                "tick": int(tick),
                "revision": 1,
            },
        )
        return thread


def link_thread_source(
    *,
    thread_id: str,
    source_kind: str,
    source_ref: str,
    relation: str = "development",
    provenance: Optional[dict[str, Any]] = None,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link one durable source to a thread; repeat links stay idempotent."""
    clean_kind, clean_ref, clean_relation = _validate_link_shape(
        source_kind, source_ref, relation
    )
    if clean_relation == "commitment":
        raise NarrativeThreadCommitmentError(
            "Commitments are established through establish_commitment only."
        )
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        # Authorization precedes resource probing: an unauthorized actor learns
        # nothing about whether the referenced source exists.
        _require_access(thread, actor_id)
        if not _source_exists(clean_kind, clean_ref):
            raise NarrativeThreadSourceError(
                f"Unknown {clean_kind} source {clean_ref!r}."
            )
        link, created = _create_link(
            thread, clean_kind, clean_ref, clean_relation, provenance, tick
        )
        if created:
            revision = _record_revision(
                thread,
                operation="linked",
                details={
                    "kind": clean_kind,
                    "ref": clean_ref,
                    "relation": clean_relation,
                },
            )
            _announce(
                "narrative_thread_linked",
                {
                    "thread_id": thread.thread_id,
                    "kind": clean_kind,
                    "ref": clean_ref,
                    "relation": clean_relation,
                    "revision": revision,
                    "tick": int(tick),
                },
            )
        return link


def link_event_to_thread(
    *,
    thread_id: str,
    event: NarrativeEvent,
    relation: str = "development",
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link a durable narrative event to a thread."""
    return link_thread_source(
        thread_id=thread_id,
        source_kind="event",
        source_ref=str(event.source_id),
        relation=relation,
        provenance={"event_type": str(event.event_type)},
        tick=tick,
        actor_id=actor_id,
    )


def link_letter_to_thread(
    *,
    thread_id: str,
    letter: LetterSend,
    relation: str = "statement",
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link a letter as a statement; never as a gameplay-establishment."""
    return link_thread_source(
        thread_id=thread_id,
        source_kind="letter",
        source_ref=str(letter.source_id),
        relation=relation,
        provenance={
            "sender_id": str(letter.sender_id),
            "recipient_id": str(letter.recipient_id),
        },
        tick=tick,
        actor_id=actor_id,
    )


def link_dialogue_turn_to_thread(
    *,
    thread_id: str,
    turn: DialogueTurn,
    relation: str = "statement",
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link preserved pair speech to a thread."""
    return link_thread_source(
        thread_id=thread_id,
        source_kind="dialogue",
        source_ref=dialogue_source_ref(turn),
        relation=relation,
        provenance={"npc_id": str(turn.npc_id), "player_id": str(turn.player_id)},
        tick=tick,
        actor_id=actor_id,
    )


def link_thread_statement(
    *,
    thread_id: str,
    source_kind: str,
    source_ref: str,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link speech or an expressed plan as a statement, never a commitment."""
    return link_thread_source(
        thread_id=thread_id,
        source_kind=source_kind,
        source_ref=source_ref,
        relation="statement",
        provenance={"channel": str(source_kind).strip()},
        tick=tick,
        actor_id=actor_id,
    )


def link_memory_to_thread(
    *,
    record: MemoryRecord,
    thread_id: str,
    actor_id: Optional[str] = None,
    tick: int = 0,
) -> StoryThreadLink:
    """Link an owner memory so explicit thread recall scope can select it.

    Tagging a memory appends a memory revision, which conservatively advances the
    owner memory generation: the linkage is a real effective-cognition change.
    """
    clean_id = _clean_thread_id(thread_id)
    ref = memory_source_ref(record)
    with transaction.atomic():
        thread = _locked_thread(clean_id)
        _require_access(thread, actor_id)
        latest = record.revisions.order_by("-revision_number").first()
        relations = dict(latest.relations) if latest is not None else {}
        if str(relations.get("thread_id", "")).strip() != clean_id:
            relations["thread_id"] = clean_id
            revise_memory(record=record, relations=relations)
        link, created = _create_link(
            thread,
            "memory",
            ref,
            "memory_reference",
            {
                "owner_id": str(record.owner_id),
                "source_id": str(record.source_id),
                "thread_id": clean_id,
            },
            tick,
        )
        if created:
            references = list(thread.memory_references)
            if ref not in references:
                references.append(ref)
            thread.memory_references = references
            revision = _record_revision(
                thread,
                operation="linked",
                details={"kind": "memory", "ref": ref, "relation": "memory_reference"},
                changed_fields={"memory_references"},
            )
            _announce(
                "narrative_thread_linked",
                {
                    "thread_id": thread.thread_id,
                    "kind": "memory",
                    "ref": ref,
                    "relation": "memory_reference",
                    "revision": revision,
                    "tick": int(tick),
                },
            )
        return link


def establish_commitment(
    *,
    thread_id: str,
    source_event_id: str,
    text: str,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Record a commitment established by a committed gameplay occurrence.

    Statement channels (claims, correspondence, private authoring) are rejected:
    an expressed willingness is remembered as speech, never as a commitment.
    """
    clean_text = str(text).strip()
    if not clean_text:
        raise NarrativeThreadCommitmentError("A commitment requires explicit text.")
    clean_event = str(source_event_id).strip()
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        event = (
            NarrativeEvent.objects.filter(source_id=clean_event).first()
            if clean_event
            else None
        )
        if event is None:
            raise NarrativeThreadCommitmentError(
                "Commitments require an existing committed gameplay event."
            )
        if event.event_type in NON_COMMITMENT_EVENT_TYPES:
            raise NarrativeThreadCommitmentError(
                f"{event.event_type!r} is a statement channel and cannot establish a commitment."
            )
        commitments = list(thread.commitments)
        if clean_text not in commitments:
            commitments.append(clean_text)
        thread.commitments = commitments
        revision = _record_revision(
            thread,
            operation="commitment_established",
            details={"event": clean_event, "event_type": str(event.event_type)},
            changed_fields={"commitments"},
        )
        _create_link(
            thread,
            "event",
            clean_event,
            "commitment",
            {"event_type": str(event.event_type)},
            tick,
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "commitment_established",
                "revision": revision,
                "state": thread.state,
                "tick": int(tick),
            },
        )
        return thread


def record_thread_development(
    *,
    thread_id: str,
    tick: int,
    source_kind: Optional[str] = None,
    source_ref: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> int:
    """Append one development tick, optionally alongside a real source link."""
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        ticks = list(thread.development_ticks)
        ticks.append(int(tick))
        thread.development_ticks = ticks
        details: dict[str, Any] = {"tick": int(tick)}
        if source_kind is not None and source_ref is not None:
            clean_kind, clean_ref, clean_relation = _validate_link_shape(
                source_kind, source_ref, "development"
            )
            if not _source_exists(clean_kind, clean_ref):
                raise NarrativeThreadSourceError(
                    f"Unknown {clean_kind} source {clean_ref!r}."
                )
            _create_link(thread, clean_kind, clean_ref, clean_relation, None, tick)
            details.update(kind=clean_kind, ref=clean_ref)
        revision = _record_revision(
            thread,
            operation="developed",
            details=details,
            changed_fields={"development_ticks"},
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "developed",
                "revision": revision,
                "state": thread.state,
                "tick": int(tick),
            },
        )
        return revision


def revise_thread_facts(
    *,
    thread_id: str,
    factual_summary: Optional[str] = None,
    unresolved_questions: Optional[Iterable[str]] = None,
    proposed_plans: Optional[Iterable[str]] = None,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> int:
    """Revise the fact/plan fields; returns the new thread revision."""
    changed: set[str] = set()
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        if factual_summary is not None:
            thread.factual_summary = str(factual_summary)
            changed.add("factual_summary")
        if unresolved_questions is not None:
            thread.unresolved_questions = [str(q) for q in unresolved_questions]
            changed.add("unresolved_questions")
        if proposed_plans is not None:
            thread.proposed_plans = [str(p) for p in proposed_plans]
            changed.add("proposed_plans")
        if not changed:
            return int(thread.revision)
        revision = _record_revision(
            thread,
            operation="revised",
            details={"fields": sorted(changed)},
            changed_fields=changed,
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "revised",
                "revision": revision,
                "state": thread.state,
                "tick": int(tick),
            },
        )
        return revision


def transition_thread(
    *,
    thread_id: str,
    new_state: str,
    reason: str,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Explicit lifecycle transition; terminal states accept no further change."""
    clean_state = str(new_state).strip()
    if clean_state not in VALID_THREAD_STATES:
        raise NarrativeThreadStateError(
            f"Invalid story thread state {clean_state!r}; must be one of {sorted(VALID_THREAD_STATES)}."
        )
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        previous = thread.state
        if previous in TERMINAL_THREAD_STATES:
            raise NarrativeThreadStateError(
                f"Story thread {thread.thread_id!r} is {previous} and cannot transition."
            )
        if previous == clean_state:
            raise NarrativeThreadStateError(
                f"Story thread {thread.thread_id!r} is already {clean_state}."
            )
        thread.state = clean_state
        revision = _record_revision(
            thread,
            operation="transitioned",
            details={"from": previous, "to": clean_state, "reason": str(reason).strip()},
            changed_fields={"state"},
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "transitioned",
                "revision": revision,
                "state": clean_state,
                "tick": int(tick),
            },
        )
        return thread


def mark_thread_dormant(
    *,
    thread_id: str,
    tick: int = 0,
    reason: str = "inactivity",
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Dormancy is the strongest outcome inactivity alone may produce."""
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        if thread.state != "active":
            return thread
        thread.state = "dormant"
        revision = _record_revision(
            thread,
            operation="dormant",
            details={"reason": str(reason).strip()},
            changed_fields={"state"},
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "dormant",
                "revision": revision,
                "state": "dormant",
                "tick": int(tick),
            },
        )
        return thread


def _thread_recency(thread: StoryThread) -> int:
    """Most recent development instant across creation, ticks, and links."""
    ticks = [int(thread.created_tick or 0)]
    ticks.extend(int(t) for t in (thread.development_ticks or []))
    last_link = (
        thread.links.order_by("-created_tick", "-id")
        .values_list("created_tick", flat=True)
        .first()
    )
    if last_link is not None:
        ticks.append(int(last_link))
    return max(ticks)


def apply_inactivity(
    *,
    thread_id: str,
    current_tick: int,
    dormant_after_ticks: int,
    actor_id: Optional[str] = None,
) -> bool:
    """Move a stale active thread to dormant; inactivity never abandons it."""
    if int(dormant_after_ticks) <= 0:
        raise NarrativeThreadError("dormant_after_ticks must be positive.")
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        if thread.state != "active":
            return False
        if int(current_tick) - _thread_recency(thread) < int(dormant_after_ticks):
            return False
        thread.state = "dormant"
        revision = _record_revision(
            thread,
            operation="dormant",
            details={"reason": "inactivity", "current_tick": int(current_tick)},
            changed_fields={"state"},
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "dormant",
                "revision": revision,
                "state": "dormant",
                "tick": int(current_tick),
            },
        )
        return True


def resolve_thread(
    *,
    thread_id: str,
    tick: int = 0,
    reason: str = "",
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Explicit resolution; quest completion never calls this by itself."""
    return transition_thread(
        thread_id=thread_id,
        new_state="resolved",
        reason=reason,
        tick=tick,
        actor_id=actor_id,
    )


def abandon_thread(
    *,
    thread_id: str,
    tick: int = 0,
    reason: str = "",
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Explicit abandonment; requires a stated reason, never plain inactivity."""
    if not str(reason).strip():
        raise NarrativeThreadStateError("Abandonment requires an explicit reason.")
    return transition_thread(
        thread_id=thread_id,
        new_state="abandoned",
        reason=reason,
        tick=tick,
        actor_id=actor_id,
    )


def note_thread_quest_completion(
    *,
    thread_id: str,
    quest_id: str,
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThread:
    """Record that a linked quest finished, without resolving the parent thread."""
    clean_quest = str(quest_id).strip()
    if not clean_quest:
        raise NarrativeThreadSourceError("quest_id must be a durable identity.")
    with transaction.atomic():
        thread = _locked_thread(thread_id)
        _require_access(thread, actor_id)
        linked = StoryThreadLink.objects.filter(
            thread=thread,
            source_kind="quest",
            source_ref=clean_quest,
            relation__in=("origin", "development"),
        ).exists()
        if not linked:
            raise NarrativeThreadSourceError(
                f"Quest {clean_quest!r} is not linked to story thread {thread.thread_id!r}."
            )
        already = StoryThreadLink.objects.filter(
            thread=thread,
            source_kind="quest",
            source_ref=clean_quest,
            relation="quest_completion",
        ).exists()
        if already:
            return thread
        _create_link(
            thread,
            "quest",
            clean_quest,
            "quest_completion",
            {"quest_id": clean_quest},
            tick,
        )
        revision = _record_revision(
            thread,
            operation="quest_completed",
            details={"quest_id": clean_quest},
        )
        _announce(
            "narrative_thread_revised",
            {
                "thread_id": thread.thread_id,
                "operation": "quest_completed",
                "revision": revision,
                "state": thread.state,
                "tick": int(tick),
            },
        )
        return thread


def link_quest_to_thread(
    *,
    thread_id: str,
    quest_id: str,
    relation: str = "development",
    tick: int = 0,
    actor_id: Optional[str] = None,
) -> StoryThreadLink:
    """Link a quest by durable identity; world/quests still owns its lifecycle."""
    return link_thread_source(
        thread_id=thread_id,
        source_kind="quest",
        source_ref=quest_id,
        relation=relation,
        provenance={"quest_id": str(quest_id).strip()},
        tick=tick,
        actor_id=actor_id,
    )
