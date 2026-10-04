"""Deterministic story-director settlement: at most one validated beat per decision.

The narrative half of the story-director boundary (design §7). It consumes a
bounded attention candidate or a confirmed creative request, captures an
immutable permissioned context snapshot, asks the generative layer for at most
one value-only beat proposal, and settles that proposal through deterministic
owner boundaries only:

* the deterministic core owns routing: a kind maps to one effect, and only
  effects with a registered owner implementation are materialized (``quest_seed``
  is deliberately unregistered until ``scenario-beat-compilation`` supplies the
  real quest boundary, so it is rejected rather than stubbed);
* narrative writes only its own data (a narrative event and thread development,
  or a letter); a relationship proposal routes through the rules owner;
* every mutable prerequisite is revalidated against the snapshot's captured
  revisions before apply, and a conflict, stale state, unsupported effect,
  unauthorized write, or unavailable target is rejected with a typed outcome
  and no partial state;
* repeated processing of one source identity after a restart returns the
  existing decision and its single beat instead of scheduling a second one.

Nothing here is a scheduler: no retry framework, no background queue. A
decision settles once, synchronously, and a beat is either materialized or not.

A decision's identity is its captured source *revision*: replaying that exact
identity (a restart, a repeated delivery) returns the durable decision and its
single beat, while a later attention run over the same thread necessarily
captures a higher revision and is a genuinely new decision. A scheduled beat's
own execution advances its thread revision, so the captured identity is
consumed exactly once and no re-drive of an old snapshot can schedule again.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Optional

from django.db import IntegrityError, transaction
from twisted.internet import defer

from world.ai.profiles import get_profile
from world.ai.story_director import (
    BEAT_KIND_CLUE,
    BEAT_KIND_FOLLOW_UP,
    BEAT_KIND_INVITATION,
    BEAT_KIND_LETTER,
    BEAT_KIND_QUEST_SEED,
    BEAT_KINDS,
    BeatProposal,
    generate_beat_proposal,
    render_director_frame,
)
from world.narrative.attention import SOURCE_REQUEST, SOURCE_THREAD, AttentionSelection
from world.narrative.authoring import validate_direction
from world.narrative.context import (
    assemble_narrative_context,
    build_budget_profile,
    persist_context_snapshot,
)
from world.narrative.correspondence import send_letter
from world.narrative.events import record_narrative_event
from world.narrative.models import (
    CreativeRequest,
    ScheduledBeat,
    StoryDirectorDecision,
    StoryThread,
)
from world.narrative.threads import (
    TERMINAL_THREAD_STATES,
    NarrativeThreadError,
    create_thread,
    find_thread,
    get_thread_revision,
    link_letter_to_thread,
    record_thread_development,
    thread_accessible,
)
from world.observability import log_info, log_warn
from world.prompts.loader import render_prompt
from world.rules.correspondence import apply_letter_relationship

DIRECTOR_CAPABILITY = "story_director"
DIRECTOR_PROMPT_VERSION = "story_director_v1"
DIRECTOR_SCHEMA_VERSION = "story_director_v1"

# Context budget: the capability contract plus one bounded context frame.
DIRECTOR_CONTEXT_WINDOW = 8192
DIRECTOR_TURN_FRAME_TARGET = 2500
DIRECTOR_TURN_FRAME_BOUND = 4000
DIRECTOR_CONTRACT_TARGET = 1400
DIRECTOR_CONTRACT_BOUND = 2200

MAX_BEATS_PER_DECISION = 1
MAX_CONTEXT_FACTS = 6
MAX_FACT_CHARACTERS = 300
MAX_CONTEXT_PARTICIPANTS = 16

# Settlement outcomes. A decision records exactly one.
OUTCOME_SCHEDULED = "scheduled"
OUTCOME_NO_CONTENT = "no_content"
OUTCOME_UNSUPPORTED_EFFECT = "unsupported_effect"
OUTCOME_UNAUTHORIZED_WRITE = "unauthorized_write"
OUTCOME_UNSUPPORTED_TARGET = "unsupported_target"
OUTCOME_INVALID_PROPOSAL = "invalid_proposal"
OUTCOME_STALE = "stale"
OUTCOME_THREAD_UNAVAILABLE = "thread_unavailable"
OUTCOME_CONFLICT = "conflict"
OUTCOME_DEDUPLICATED = "deduplicated"

# Effects. The kind -> effect table is the single place where the deterministic
# core decides what a beat means; a proposal never asserts its own routing.
EFFECT_NARRATIVE_STATEMENT = "narrative_statement"
EFFECT_LETTER_SEND = "letter_send"
EFFECT_QUEST_SEED = "quest_seed"

EFFECT_BY_KIND: dict[str, str] = {
    BEAT_KIND_FOLLOW_UP: EFFECT_NARRATIVE_STATEMENT,
    BEAT_KIND_CLUE: EFFECT_NARRATIVE_STATEMENT,
    BEAT_KIND_INVITATION: EFFECT_NARRATIVE_STATEMENT,
    BEAT_KIND_LETTER: EFFECT_LETTER_SEND,
    BEAT_KIND_QUEST_SEED: EFFECT_QUEST_SEED,
}

# The executable registry: only effects with a real deterministic owner handler.
# ``quest_seed`` is absent on purpose until scenario-beat-compilation registers
# the quest boundary; an absent effect is rejected, never stubbed.
EXECUTABLE_EFFECTS: frozenset[str] = frozenset(
    {EFFECT_NARRATIVE_STATEMENT, EFFECT_LETTER_SEND}
)

NARRATIVE_BEAT_EVENT_TYPE = "story_beat"


class DirectorError(Exception):
    """Base exception for director settlement."""


class DirectorAccessError(DirectorError):
    """Raised when a decision source does not belong to the acting owner."""


class DirectorSourceError(DirectorError):
    """Raised when a decision source is not an eligible bounded source."""


class _EffectRejected(DirectorError):
    """An effect-specific prerequisite failed; the savepoint rolls back."""

    def __init__(self, outcome: str):
        self.outcome = outcome
        super().__init__(outcome)


@dataclass(frozen=True)
class DirectorSource:
    """The immutable identity a decision was prepared against."""

    kind: str
    ref: str
    revision: int
    thread_id: str = ""


@dataclass(frozen=True)
class DirectorInvocation:
    """One prepared decision: captured source, revisions, and exact messages."""

    owner_id: str
    source: DirectorSource
    thread_revision: int
    snapshot_id: str
    context_frame: str
    messages: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class BeatOutcome:
    """The durable result of one settlement."""

    decision: StoryDirectorDecision
    beat: Optional[ScheduledBeat]
    outcome: str

    @property
    def scheduled(self) -> bool:
        return self.beat is not None


def _announce(event: str, boundary: Mapping[str, Any]) -> None:
    """Emit one boundary info event once the surrounding transaction commits."""
    payload = dict(boundary)
    transaction.on_commit(lambda: log_info(event, context=payload))


# Rejections log synchronously (not through ``on_commit``): the message is the
# only trace of a refused decision, and a rolled-back settle would otherwise
# lose it entirely (the same rationale as the dream-session reject helper).


def _reject_boundary(
    handle: str,
    invocation: "DirectorInvocation",
    reason: str,
    now_tick: int,
    *,
    thread_id: str = "",
    arrangement_revision: int = 0,
) -> dict[str, Any]:
    """IDs and counts only for a rejection event; never proposal prose."""
    boundary: dict[str, Any] = {
        "decision_id": handle,
        "owner": invocation.owner_id,
        "source_kind": invocation.source.kind,
        "source_ref": invocation.source.ref,
        "thread_id": thread_id or invocation.source.thread_id,
        "reason": reason,
        "tick": int(now_tick),
    }
    if arrangement_revision:
        boundary["arrangement_revision"] = int(arrangement_revision)
    return boundary


def decision_id_for(
    owner_id: Any, source_kind: Any, source_ref: Any, source_revision: Any
) -> str:
    """Deterministic decision identity for one immutable source revision.

    Every component is normalized (stripped) so a pre-generation dedupe lookup
    and the persisted handle always agree on the same identity.
    """
    key = (
        f"{str(owner_id).strip()}:{str(source_kind).strip()}:"
        f"{str(source_ref).strip()}:v{int(source_revision)}"
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"dec_{digest[:48]}"


def beat_id_for(decision_id: str) -> str:
    """Deterministic beat identity: at most one beat per decision."""
    return f"beat:{decision_id}"


def execution_ref_for(decision_id: str) -> str:
    """Deterministic durable identity of the record a beat effect produces."""
    return f"nbeat:{decision_id}"


def find_decision(
    owner_id: Any, source_kind: Any, source_ref: Any, source_revision: Any
) -> Optional[StoryDirectorDecision]:
    """The decision already recorded for one source revision, or None."""
    handle = decision_id_for(owner_id, source_kind, source_ref, source_revision)
    return StoryDirectorDecision.objects.filter(decision_id=handle).first()


def _resolve_character(identity: Any) -> Any:
    """Resolve a character identity to its live object, or None (never raises)."""
    from evennia.objects.models import ObjectDB

    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import NPC

    try:
        pk = int(str(identity).strip())
    except (TypeError, ValueError):
        # observability: ignore R2: a non-numeric identity is simply unresolvable
        return None
    obj = ObjectDB.objects.filter(pk=pk).first()
    if obj is None or not isinstance(obj, (PlayerCharacter, NPC)):
        return None
    return obj


def _require_accessible_thread(thread: Optional[StoryThread], owner_id: str) -> StoryThread:
    if thread is None or not thread_accessible(thread, owner_id):
        raise DirectorAccessError("The decision source is not accessible to its owner.")
    if thread.state in TERMINAL_THREAD_STATES:
        raise DirectorSourceError("A terminal story thread cannot continue.")
    return thread


def resolve_source(
    owner_id: Any,
    *,
    candidate: Optional[AttentionSelection] = None,
    request: Optional[CreativeRequest] = None,
) -> DirectorSource:
    """Resolve the single eligible decision source, or raise ``DirectorSourceError``.

    An automatic source must be a bounded attention selection over an existing
    invested thread; an unrelated new story is eligible only as an explicitly
    confirmed, valid creative request version. Passing both (or neither) is a
    shaped refusal, not a guess.
    """
    clean_owner = str(owner_id).strip()
    if not clean_owner:
        raise DirectorSourceError("A decision requires an owning identity.")
    if (candidate is None) == (request is None):
        raise DirectorSourceError(
            "A decision uses exactly one bounded candidate or confirmed request."
        )

    if request is not None:
        if str(request.owner_id) != clean_owner:
            raise DirectorAccessError("This creative request is not yours.")
        if str(request.validation_status) != "valid":
            raise DirectorSourceError("Only a validated creative request is eligible.")
        validation = validate_direction(request.direction, owner_id=clean_owner)
        if not validation.valid:
            raise DirectorSourceError("The creative request no longer validates.")
        thread_id = str(validation.direction.get("thread_id") or "")
        if thread_id:
            _require_accessible_thread(find_thread(thread_id), clean_owner)
        return DirectorSource(
            kind=SOURCE_REQUEST,
            ref=str(request.submission_key),
            revision=int(request.version),
            thread_id=thread_id,
        )

    assert candidate is not None  # narrowed by the exactly-one check above
    inner = candidate.candidate
    if inner.source_kind != SOURCE_THREAD:
        raise DirectorSourceError(
            "An automatic source must continue an existing invested thread; "
            "an unrelated new story requires a confirmed creative request."
        )
    thread = _require_accessible_thread(find_thread(inner.source_ref), clean_owner)
    return DirectorSource(
        kind=SOURCE_THREAD,
        ref=thread.thread_id,
        revision=int(inner.revision),
        thread_id=thread.thread_id,
    )


def _bounded_text(value: Any, limit: int = MAX_FACT_CHARACTERS) -> str:
    return str(value or "")[:limit]


def _context_payload(
    owner_id: str,
    source: DirectorSource,
    thread: Optional[StoryThread],
    request: Optional[CreativeRequest],
) -> dict[str, Any]:
    """The bounded, permissioned facts a director decision may see."""
    payload: dict[str, Any] = {
        "owner": owner_id,
        "source": {
            "kind": source.kind,
            "ref": source.ref,
            "revision": source.revision,
        },
        "kinds": sorted(BEAT_KINDS),
        "max_beats": MAX_BEATS_PER_DECISION,
    }
    if thread is not None:
        payload["thread"] = {
            "id": thread.thread_id,
            "state": thread.state,
            "revision": int(thread.revision),
            "participants": [
                str(item) for item in (thread.participants or [])[:MAX_CONTEXT_PARTICIPANTS]
            ],
            "facts": _bounded_text(thread.factual_summary).splitlines()[:MAX_CONTEXT_FACTS],
            "unresolved": [
                _bounded_text(item)
                for item in (thread.unresolved_questions or [])[:MAX_CONTEXT_FACTS]
            ],
        }
    else:
        payload["thread"] = {"id": "", "state": "new", "revision": 0}
    if request is not None:
        direction = request.direction or {}
        payload["request"] = {
            "submission_key": str(request.submission_key),
            "version": int(request.version),
            "summary": _bounded_text(direction.get("summary")),
            "themes": [
                _bounded_text(item, 80) for item in (direction.get("themes") or [])[:MAX_CONTEXT_FACTS]
            ],
            "participants": [
                _bounded_text(item, 80)
                for item in (direction.get("participants") or [])[:MAX_CONTEXT_PARTICIPANTS]
            ],
        }
    return payload


def _owner_anchor(
    owner_id: str, thread: Optional[StoryThread], request: Optional[CreativeRequest]
) -> str:
    """The mandatory character-anchor section: only owner-permitted identity."""
    anchor: dict[str, Any] = {"owner": owner_id}
    if thread is not None:
        anchor["participants"] = [
            str(item) for item in (thread.participants or [])[:MAX_CONTEXT_PARTICIPANTS]
        ]
    if request is not None:
        anchor["request"] = str(request.submission_key)
    return json.dumps(anchor, ensure_ascii=False, sort_keys=True)


def prepare_decision(
    owner_id: Any, *, source: DirectorSource, now_tick: int = 0
) -> DirectorInvocation:
    """Capture the immutable permissioned context for one decision source.

    The snapshot, not a live read, is what generation and settlement both use;
    its captured thread revisions are the identities settlement revalidates.
    """
    clean_owner = str(owner_id).strip()
    thread = find_thread(source.thread_id) if source.thread_id else None
    request = (
        CreativeRequest.objects.filter(submission_key=source.ref).first()
        if source.kind == SOURCE_REQUEST
        else None
    )
    frame = render_director_frame(_context_payload(clean_owner, source, thread, request))
    budget = build_budget_profile(
        get_profile(DIRECTOR_CAPABILITY),
        context_window=DIRECTOR_CONTEXT_WINDOW,
        section_targets={
            "turn_frames": DIRECTOR_TURN_FRAME_TARGET,
            "capability_contract": DIRECTOR_CONTRACT_TARGET,
        },
        section_bounds={
            "turn_frames": DIRECTOR_TURN_FRAME_BOUND,
            "capability_contract": DIRECTOR_CONTRACT_BOUND,
        },
    )
    assembled = assemble_narrative_context(
        capability=DIRECTOR_CAPABILITY,
        prompt_version=DIRECTOR_PROMPT_VERSION,
        schema_version=DIRECTOR_SCHEMA_VERSION,
        owner_id=clean_owner,
        requester_id=clean_owner,
        budget_profile=budget,
        global_rules=render_prompt("npc_dialogue.global_rules"),
        capability_contract=render_prompt("story_director.system"),
        character_anchor=_owner_anchor(clean_owner, thread, request),
        turn_frames=(frame,),
        thread_id=source.thread_id,
    )
    snapshot = persist_context_snapshot(assembled)
    captured_revision = (
        get_thread_revision(source.thread_id) if source.thread_id else 0
    )
    _announce(
        "story_director_decision_prepared",
        {
            "owner": clean_owner,
            "source_kind": source.kind,
            "source_ref": source.ref,
            "source_revision": source.revision,
            "thread_id": source.thread_id,
            "thread_revision": captured_revision,
            "snapshot_id": snapshot.snapshot_id,
            "tick": int(now_tick),
        },
    )
    return DirectorInvocation(
        owner_id=clean_owner,
        source=source,
        thread_revision=captured_revision,
        snapshot_id=snapshot.snapshot_id,
        context_frame=frame,
        messages=assembled.to_messages(),
    )


def _proposal_rejection(
    proposal: Any, participants: frozenset[str], owner_id: str
) -> Optional[str]:
    """The first deterministic gate a proposal fails, or None when acceptable."""
    if not isinstance(proposal, BeatProposal):
        return OUTCOME_INVALID_PROPOSAL
    if proposal.writes:
        return OUTCOME_UNAUTHORIZED_WRITE
    effect = EFFECT_BY_KIND.get(proposal.kind)
    if effect is None or effect not in EXECUTABLE_EFFECTS:
        return OUTCOME_UNSUPPORTED_EFFECT
    summary = proposal.summary.strip()
    if not summary or len(summary) > 600:
        return OUTCOME_INVALID_PROPOSAL
    needs_counterpart = effect == EFFECT_LETTER_SEND or proposal.relation_delta > 0
    if needs_counterpart:
        counterpart = _resolve_character(proposal.recipient)
        from typeclasses.npcs import NPC

        if not isinstance(counterpart, NPC):
            return OUTCOME_UNSUPPORTED_TARGET
        if str(counterpart.pk) not in participants:
            return OUTCOME_UNSUPPORTED_TARGET
        if effect == EFFECT_LETTER_SEND:
            from typeclasses.characters import PlayerCharacter

            if not isinstance(_resolve_character(owner_id), PlayerCharacter):
                return OUTCOME_UNSUPPORTED_TARGET
    return None


def _select_proposal(
    proposals: Iterable[Any], participants: frozenset[str], owner_id: str
) -> tuple[Optional[BeatProposal], str]:
    """Choose at most one materializable proposal; report the first refusal."""
    first_reason: Optional[str] = None
    for proposal in proposals or ():
        reason = _proposal_rejection(proposal, participants, owner_id)
        if reason is None:
            return proposal, OUTCOME_SCHEDULED
        if first_reason is None:
            first_reason = reason
    return None, (first_reason or OUTCOME_NO_CONTENT)


def new_story_thread_id(decision_id: str) -> str:
    """Deterministic thread identity a confirmed new-story beat would own."""
    return f"story:{decision_id}"


def _lock_existing_thread(invocation: DirectorInvocation) -> Optional[StoryThread]:
    """Lock the source's thread row; a new-story source has none yet."""
    if not invocation.source.thread_id:
        return None
    return (
        StoryThread.objects.select_for_update()
        .filter(thread_id=invocation.source.thread_id)
        .first()
    )


def _create_new_story_thread(
    invocation: DirectorInvocation, thread_id: str, now_tick: int
) -> StoryThread:
    """Create the thread a confirmed new-story beat owns, exactly once."""
    try:
        create_thread(
            thread_id=thread_id,
            origin=f"request:{invocation.source.ref}",
            participants=[invocation.owner_id],
            visible_to=[invocation.owner_id],
            tick=int(now_tick),
        )
    except NarrativeThreadError:
        raced = StoryThread.objects.filter(thread_id=thread_id).first()
        if raced is None:
            raise
    thread = StoryThread.objects.filter(thread_id=thread_id).first()
    if thread is None:
        raise DirectorError(f"story thread {thread_id!r} could not be created")
    return thread


def _record_decision(
    invocation: DirectorInvocation,
    outcome: str,
    *,
    now_tick: int,
    thread: Optional[StoryThread],
) -> StoryDirectorDecision:
    source = invocation.source
    return StoryDirectorDecision.objects.create(
        decision_id=decision_id_for(
            invocation.owner_id, source.kind, source.ref, source.revision
        ),
        owner_id=invocation.owner_id,
        source_kind=source.kind,
        source_ref=source.ref,
        source_revision=int(source.revision),
        thread_id=thread.thread_id if thread is not None else source.thread_id,
        thread_revision=int(thread.revision) if thread is not None else 0,
        outcome=outcome,
        scheduled=outcome == OUTCOME_SCHEDULED,
        snapshot_id=invocation.snapshot_id,
        created_tick=int(now_tick),
    )


def _apply_effect(
    effect: str,
    proposal: BeatProposal,
    invocation: DirectorInvocation,
    thread: StoryThread,
    execution_ref: str,
    now_tick: int,
) -> None:
    """Materialize one accepted beat through the deterministic owners."""
    participants = [invocation.owner_id] + [
        str(item) for item in (thread.participants or [])
    ]
    if effect == EFFECT_NARRATIVE_STATEMENT:
        record_narrative_event(
            source_id=execution_ref,
            event_type=NARRATIVE_BEAT_EVENT_TYPE,
            content={"beat_kind": proposal.kind, "summary": proposal.summary.strip()},
            participants=participants,
            location="",
            tick=int(now_tick),
            visibility="private",
            salience=2,
        )
        record_thread_development(
            thread_id=thread.thread_id,
            tick=int(now_tick),
            source_kind="event",
            source_ref=execution_ref,
            actor_id=invocation.owner_id,
        )
    elif effect == EFFECT_LETTER_SEND:
        counterpart = _resolve_character(proposal.recipient)
        owner_char = _resolve_character(invocation.owner_id)
        letter = send_letter(
            sender_id=counterpart.pk,
            recipient_id=owner_char.pk,
            body=proposal.summary.strip(),
            source_id=execution_ref,
        )
        link_letter_to_thread(
            thread_id=thread.thread_id,
            letter=letter,
            relation="statement",
            tick=int(now_tick),
            actor_id=invocation.owner_id,
        )
    if proposal.relation_delta > 0:
        # A relationship change is rules-owned data: narrative never writes it
        # itself, it routes the value to the rules applier.
        counterpart = _resolve_character(proposal.recipient)
        owner_char = _resolve_character(invocation.owner_id)
        outcome = apply_letter_relationship(
            counterpart, owner_char, proposal.relation_delta
        )
        if outcome is None or getattr(outcome, "source_rejected", False):
            raise _EffectRejected(OUTCOME_UNSUPPORTED_TARGET)


def settle_decision(
    *, invocation: DirectorInvocation, proposals: Iterable[Any], now_tick: int = 0
) -> BeatOutcome:
    """Settle one decision: schedule at most one materializable beat, or none.

    Idempotent on the source identity; stale-state, conflict, unsupported-effect,
    unauthorized-write and unavailable-target outcomes all leave the thread and
    every unauthorized owner untouched.
    """
    source = invocation.source
    handle = decision_id_for(
        invocation.owner_id, source.kind, source.ref, source.revision
    )
    existing = StoryDirectorDecision.objects.filter(decision_id=handle).first()
    if existing is not None:
        return _outcome_for_decision(existing, OUTCOME_DEDUPLICATED, now_tick)

    try:
        return _settle_once(
            invocation=invocation, proposals=proposals, now_tick=now_tick, handle=handle
        )
    except IntegrityError:
        # A concurrent settlement of the same source won the unique source
        # constraint; its row is the durable decision and its beat the durable
        # arrangement, so this settlement deduplicates instead of failing.
        raced = StoryDirectorDecision.objects.filter(decision_id=handle).first()
        if raced is None:
            raise
        return BeatOutcome(
            decision=raced,
            beat=ScheduledBeat.objects.filter(decision=raced).first(),
            outcome=raced.outcome,
        )


def _settle_once(
    *,
    invocation: DirectorInvocation,
    proposals: Iterable[Any],
    now_tick: int,
    handle: str,
) -> BeatOutcome:
    """One single-transaction settlement; the caller dedupes and catches races."""
    source = invocation.source
    with transaction.atomic():
        thread = _lock_existing_thread(invocation)
        pending_thread_id = ""
        if source.thread_id:
            if thread is None:
                decision = _record_decision(
                    invocation,
                    OUTCOME_THREAD_UNAVAILABLE,
                    now_tick=now_tick,
                    thread=None,
                )
                log_warn(
                    "story_director_decision_rejected",
                    context=_reject_boundary(
                        handle, invocation, OUTCOME_THREAD_UNAVAILABLE, now_tick
                    ),
                )
                return BeatOutcome(
                    decision=decision, beat=None, outcome=decision.outcome
                )
            # Revalidate mutable prerequisites against the captured state: a
            # thread that became terminal or lost its owner's visibility is
            # unavailable.
            if thread.state in TERMINAL_THREAD_STATES or not thread_accessible(
                thread, invocation.owner_id
            ):
                decision = _record_decision(
                    invocation,
                    OUTCOME_THREAD_UNAVAILABLE,
                    now_tick=now_tick,
                    thread=thread,
                )
                log_warn(
                    "story_director_decision_rejected",
                    context=_reject_boundary(
                        handle,
                        invocation,
                        OUTCOME_THREAD_UNAVAILABLE,
                        now_tick,
                        thread_id=thread.thread_id,
                    ),
                )
                return BeatOutcome(
                    decision=decision, beat=None, outcome=decision.outcome
                )
            if int(thread.revision) != int(invocation.thread_revision):
                decision = _record_decision(
                    invocation, OUTCOME_STALE, now_tick=now_tick, thread=thread
                )
                stale = _reject_boundary(
                    handle,
                    invocation,
                    OUTCOME_STALE,
                    now_tick,
                    thread_id=thread.thread_id,
                )
                stale["captured_revision"] = int(invocation.thread_revision)
                stale["current_revision"] = int(thread.revision)
                log_warn("story_director_decision_stale", context=stale)
                return BeatOutcome(
                    decision=decision, beat=None, outcome=decision.outcome
                )
            participants = frozenset(
                str(item) for item in (thread.participants or [])
            )
        else:
            # A confirmed new story owns a deterministic thread, but the row is
            # created only when a beat actually materializes, so a rejected or
            # empty decision leaves no orphan thread (and no attention
            # candidate) behind.
            pending_thread_id = new_story_thread_id(handle)
            occupied = StoryThread.objects.filter(
                thread_id=pending_thread_id
            ).first()
            if occupied is not None:
                decision = _record_decision(
                    invocation, OUTCOME_CONFLICT, now_tick=now_tick, thread=occupied
                )
                log_warn(
                    "story_director_decision_conflict",
                    context=_reject_boundary(
                        handle,
                        invocation,
                        OUTCOME_CONFLICT,
                        now_tick,
                        thread_id=occupied.thread_id,
                        arrangement_revision=int(occupied.revision),
                    ),
                )
                return BeatOutcome(
                    decision=decision, beat=None, outcome=decision.outcome
                )
            participants = frozenset({invocation.owner_id})

        proposal, reason = _select_proposal(
            proposals, participants, invocation.owner_id
        )
        if proposal is None:
            decision = _record_decision(
                invocation, reason, now_tick=now_tick, thread=thread
            )
            log_warn(
                "story_director_decision_rejected",
                context=_reject_boundary(
                    handle,
                    invocation,
                    reason,
                    now_tick,
                    thread_id=thread.thread_id if thread is not None else "",
                ),
            )
            return BeatOutcome(decision=decision, beat=None, outcome=decision.outcome)

        effect = EFFECT_BY_KIND[proposal.kind]
        execution_ref = execution_ref_for(handle)
        beat: Optional[ScheduledBeat] = None
        target: Optional[StoryThread] = thread
        arrangement_revision = 0
        try:
            with transaction.atomic():
                if target is None:
                    # The new-story thread is created inside the savepoint so a
                    # later failure removes it together with the beat.
                    target = _create_new_story_thread(
                        invocation, pending_thread_id, now_tick
                    )
                arrangement_revision = int(target.revision)
                if ScheduledBeat.objects.filter(
                    thread=target, arrangement_revision=arrangement_revision
                ).exists():
                    raise _EffectRejected(OUTCOME_CONFLICT)
                beat = ScheduledBeat.objects.create(
                    beat_id=beat_id_for(handle),
                    decision=_record_decision(
                        invocation,
                        OUTCOME_SCHEDULED,
                        now_tick=now_tick,
                        thread=target,
                    ),
                    owner_id=invocation.owner_id,
                    thread=target,
                    kind=proposal.kind,
                    effect=effect,
                    arrangement_revision=arrangement_revision,
                    payload={
                        "kind": proposal.kind,
                        "summary": proposal.summary.strip(),
                        "recipient": proposal.recipient,
                        "relation_delta": proposal.relation_delta,
                    },
                    execution_ref=execution_ref,
                    created_tick=int(now_tick),
                )
                _apply_effect(
                    effect, proposal, invocation, target, execution_ref, now_tick
                )
        except _EffectRejected as rejected:
            decision = _record_decision(
                invocation, rejected.outcome, now_tick=now_tick, thread=thread
            )
            log_warn(
                (
                    "story_director_decision_conflict"
                    if rejected.outcome == OUTCOME_CONFLICT
                    else "story_director_decision_rejected"
                ),
                context=_reject_boundary(
                    handle,
                    invocation,
                    rejected.outcome,
                    now_tick,
                    thread_id=target.thread_id if target is not None else "",
                    arrangement_revision=arrangement_revision,
                ),
            )
            return BeatOutcome(decision=decision, beat=None, outcome=decision.outcome)
        except IntegrityError:
            raced = StoryDirectorDecision.objects.filter(decision_id=handle).first()
            if raced is not None:
                # A concurrent settlement of the same source won the unique
                # source constraint; its row is the durable decision.
                return BeatOutcome(
                    decision=raced,
                    beat=ScheduledBeat.objects.filter(decision=raced).first(),
                    outcome=raced.outcome,
                )
            decision = _record_decision(
                invocation, OUTCOME_CONFLICT, now_tick=now_tick, thread=thread
            )
            log_warn(
                "story_director_decision_conflict",
                context=_reject_boundary(
                    handle,
                    invocation,
                    OUTCOME_CONFLICT,
                    now_tick,
                    thread_id=target.thread_id if target is not None else "",
                    arrangement_revision=arrangement_revision,
                ),
            )
            return BeatOutcome(decision=decision, beat=None, outcome=decision.outcome)

        _announce(
            "story_director_beat_scheduled",
            {
                "decision_id": handle,
                "beat_id": beat.beat_id,
                "owner": invocation.owner_id,
                "thread_id": target.thread_id,
                "kind": proposal.kind,
                "effect": effect,
                "tick": int(now_tick),
            },
        )
        return BeatOutcome(decision=beat.decision, beat=beat, outcome=OUTCOME_SCHEDULED)


def _outcome_for_decision(
    decision: StoryDirectorDecision, outcome: str, now_tick: int
) -> BeatOutcome:
    """Return an already-durable decision (and its single beat) unchanged."""
    beat = ScheduledBeat.objects.filter(decision=decision).first()
    if outcome == OUTCOME_DEDUPLICATED:
        _announce(
            "story_director_decision_reused",
            {
                "decision_id": decision.decision_id,
                "owner": decision.owner_id,
                "outcome": decision.outcome,
                "tick": int(now_tick),
            },
        )
    return BeatOutcome(decision=decision, beat=beat, outcome=decision.outcome)


@defer.inlineCallbacks
def attempt_decision(
    owner_id: Any,
    *,
    client: Any,
    candidate: Optional[AttentionSelection] = None,
    request: Optional[CreativeRequest] = None,
    now_tick: int = 0,
):
    """One intentional director attempt: dedupe, capture, generate, settle.

    Repeated processing of one source revision returns the durable decision
    without a second model call, so a restart cannot schedule a duplicate beat.
    """
    source = resolve_source(owner_id, candidate=candidate, request=request)
    existing = find_decision(
        owner_id, source.kind, source.ref, source.revision
    )
    if existing is not None:
        return _outcome_for_decision(existing, OUTCOME_DEDUPLICATED, now_tick)
    invocation = prepare_decision(owner_id, source=source, now_tick=now_tick)
    proposal = yield generate_beat_proposal(client, invocation.messages)
    proposals: tuple[Any, ...] = (proposal,) if proposal is not None else ()
    return settle_decision(
        invocation=invocation, proposals=proposals, now_tick=now_tick
    )
