"""Deterministic narrative attention: eligibility filtering and bounded ranking.

Attention is the deterministic boundary that narrows the narrative directions a
later director may pursue. It never generates prose, never calls a model, and
never persists a beat: :func:`rank_attention` is a pure function over plain
immutable candidate/context values, and :func:`build_attention_candidates` is
its read-only durable extraction layer.

An automatic candidate is eligible only when the owner already knows the
invested story it continues; an unrelated new story is eligible only as an
explicitly confirmed creative request version. Knowledge, location, scheduling
and executable feasibility are filtered before any scoring runs, so a
high-salience but ineligible candidate can never out-rank an eligible one.

The bounded result reports reason codes and immutable source references
(identity + revision), so a director can revalidate changed state instead of
acting on a stale snapshot. ``snapshot_hash`` fingerprints the inputs and
calibration configuration, not the resulting order.

Weights and focus limits are calibration choices recorded in
:mod:`world.narrative.attention_calibration` and the committed
``attention_calibration_report.json``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from world.observability import log_info, log_warn

ATTENTION_CONFIG_VERSION = "attention_v1"

# Deterministic capabilities that already have an owning deterministic
# implementation able to materialize a beat. A candidate whose capability is
# outside this set is not executable regardless of its score.
IMPLEMENTED_CAPABILITIES = frozenset({"dialogue", "letter", "quest"})

SOURCE_THREAD = "thread"
SOURCE_REQUEST = "request"

# Exclusion reason codes (stable identifiers, safe for logs).
REASON_UNKNOWN_TO_OWNER = "unknown_to_owner"
REASON_NOT_INVESTED = "not_invested"
REASON_LOCATION_UNREACHABLE = "location_unreachable"
REASON_SCHEDULE_BLOCKED = "schedule_blocked"
REASON_NOT_EXECUTABLE = "not_executable"
REASON_SUPERSEDED_REQUEST = "superseded_request"

# Selection reason codes.
REASON_SELECTED = "selected"
REASON_BELOW_FOCUS_LIMIT = "below_focus_limit"
REASON_IN_COOLDOWN = "in_cooldown"
REASON_REPEATED = "repeated"

# Correspondence receipt is passive: a read/collection never counts as
# participation even though it writes an owner-participant narrative event.
PASSIVE_RECEIPT_EVENT_TYPES = frozenset({"correspondence_read"})

# Read bounds so extraction never scans an unbounded history.
MAX_CONSIDERED_THREADS = 500
MAX_ENGAGEMENT_EVENTS = 5000
DEFAULT_ENGAGEMENT_WINDOW_TICKS = 30 * 24 * 3600


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return float(value)


@dataclass(frozen=True)
class EngagementSignals:
    """Observable engagement evidence extracted from durable records.

    ``passive_receipts`` is recorded for provenance but contributes nothing to
    the engagement score: receiving or reading is not high engagement.
    """

    dialogue_initiations: int = 0
    sustained_correspondence: int = 0
    clue_questions: int = 0
    participation: int = 0
    passive_receipts: int = 0


@dataclass(frozen=True)
class AttentionCandidate:
    """One plain immutable attention candidate (never a live ORM row)."""

    candidate_id: str
    source_kind: str
    source_ref: str
    revision: int
    origin: str
    participants: tuple[str, ...] = ()
    invested: bool = False
    confirmed: bool = False
    knowledge: bool = False
    authoritative: bool = True
    required_location: str = ""
    capability: str = ""
    unresolved_stakes: int = 0
    relationship: int = 0
    deadline_tick: Optional[int] = None
    engagement: EngagementSignals = field(default_factory=EngagementSignals)
    repetition: int = 0
    last_activity_tick: Optional[int] = None
    salience: int = 0


@dataclass(frozen=True)
class AttentionContext:
    """The deterministic owner-side facts eligibility needs, never a model."""

    owner_id: str
    now_tick: int
    owner_location: str = ""
    reachable_locations: frozenset[str] = frozenset()
    blocked_participants: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AttentionWeights:
    """Weights for the named ranking components (calibration values)."""

    stakes: float = 1.0
    engagement: float = 1.2
    relationship: float = 1.0
    deadline: float = 1.5
    location: float = 0.5
    repetition: float = 0.6
    cooldown: float = 0.8


@dataclass(frozen=True)
class EngagementWeights:
    """Relative weights of the observable engagement signals."""

    dialogue_initiation: float = 1.0
    correspondence: float = 1.0
    clue_question: float = 1.5
    participation: float = 1.0


@dataclass(frozen=True)
class AttentionConfig:
    """The committed calibration choice for one attention ranking run."""

    version: str = ATTENTION_CONFIG_VERSION
    weights: AttentionWeights = field(default_factory=AttentionWeights)
    engagement_weights: EngagementWeights = field(default_factory=EngagementWeights)
    focus_limit: int = 3
    cooldown_ticks: int = 3600
    stakes_saturation: int = 3
    engagement_saturation: float = 4.0
    relationship_saturation: int = 50
    deadline_horizon_ticks: int = 24 * 3600
    repetition_saturation: int = 4


DEFAULT_ATTENTION_CONFIG = AttentionConfig()


@dataclass(frozen=True)
class AttentionComponent:
    """One named scoring component after normalization and weighting."""

    name: str
    raw: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class AttentionSourceRef:
    """Immutable source identity + revision a director must revalidate."""

    candidate_id: str
    source_ref: str
    revision: int


@dataclass(frozen=True)
class AttentionSelection:
    """One eligible candidate with its deterministic score and reasons."""

    candidate: AttentionCandidate
    score: float
    components: tuple[AttentionComponent, ...]
    reason_codes: tuple[str, ...]
    selected: bool

    @property
    def candidate_id(self) -> str:
        """The stable candidate identity, for directed reads and logging."""
        return self.candidate.candidate_id


@dataclass(frozen=True)
class AttentionExclusion:
    """One ineligible candidate with the reasons established before ranking."""

    candidate: AttentionCandidate
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        """The stable candidate identity, for directed reads and logging."""
        return self.candidate.candidate_id


@dataclass(frozen=True)
class AttentionDecision:
    """The bounded attention result handed to a later director.

    ``selected`` is the focus-bounded set; ``ranked`` is every eligible
    candidate in order; ``excluded`` records why each ineligible candidate was
    filtered before scoring. No row is mutated, so unselected state survives.
    """

    config_version: str
    owner_id: str
    now_tick: int
    focus_limit: int
    selected: tuple[AttentionSelection, ...]
    ranked: tuple[AttentionSelection, ...]
    excluded: tuple[AttentionExclusion, ...]
    sources: tuple[AttentionSourceRef, ...]
    snapshot_hash: str
    reason_counts: tuple[tuple[str, int], ...]


def eligibility_reasons(
    candidate: AttentionCandidate,
    context: AttentionContext,
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> tuple[str, ...]:
    """Establish every pre-scoring exclusion for one candidate, in stable order."""
    reasons: list[str] = []
    if not candidate.knowledge:
        reasons.append(REASON_UNKNOWN_TO_OWNER)
    if candidate.source_kind == SOURCE_REQUEST and not candidate.authoritative:
        reasons.append(REASON_SUPERSEDED_REQUEST)
    if not (candidate.invested or candidate.confirmed):
        reasons.append(REASON_NOT_INVESTED)
    if candidate.capability not in IMPLEMENTED_CAPABILITIES:
        reasons.append(REASON_NOT_EXECUTABLE)
    if (
        candidate.required_location
        and candidate.required_location != context.owner_location
        and candidate.required_location not in context.reachable_locations
    ):
        reasons.append(REASON_LOCATION_UNREACHABLE)
    if set(candidate.participants) & context.blocked_participants:
        reasons.append(REASON_SCHEDULE_BLOCKED)
    return tuple(reasons)


def _engagement_raw(candidate: AttentionCandidate, config: AttentionConfig) -> float:
    signals = candidate.engagement
    weights = config.engagement_weights
    active = (
        signals.dialogue_initiations * weights.dialogue_initiation
        + signals.sustained_correspondence * weights.correspondence
        + signals.clue_questions * weights.clue_question
        + signals.participation * weights.participation
    )
    # Passive receipts are deliberately absent from the sum.
    if config.engagement_saturation <= 0:
        return _clamp01(active)
    return _clamp01(active / config.engagement_saturation)


def _deadline_raw(
    deadline_tick: Optional[int], now_tick: int, config: AttentionConfig
) -> float:
    if deadline_tick is None:
        return 0.0
    if deadline_tick <= now_tick:
        return 1.0
    if config.deadline_horizon_ticks <= 0:
        return 1.0
    return _clamp01(1.0 - (deadline_tick - now_tick) / config.deadline_horizon_ticks)


def _location_raw(required_location: str, context: AttentionContext) -> float:
    if required_location == context.owner_location:
        return 1.0
    if not required_location or required_location in context.reachable_locations:
        return 0.5
    return 0.0


def _cooldown_raw(
    last_activity_tick: Optional[int], now_tick: int, config: AttentionConfig
) -> float:
    if last_activity_tick is None or config.cooldown_ticks <= 0:
        return 0.0
    elapsed = now_tick - last_activity_tick
    if elapsed >= config.cooldown_ticks:
        return 0.0
    return _clamp01(1.0 - elapsed / config.cooldown_ticks)


def score_candidate(
    candidate: AttentionCandidate,
    context: AttentionContext,
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> AttentionSelection:
    """Deterministically score one eligible candidate with named components."""
    weights = config.weights
    stakes_raw = (
        _clamp01(candidate.unresolved_stakes / config.stakes_saturation)
        if config.stakes_saturation > 0
        else _clamp01(float(candidate.unresolved_stakes))
    )
    engagement_raw = _engagement_raw(candidate, config)
    relationship_raw = (
        _clamp01(candidate.relationship / config.relationship_saturation)
        if config.relationship_saturation > 0
        else _clamp01(float(candidate.relationship))
    )
    deadline_raw = _deadline_raw(candidate.deadline_tick, context.now_tick, config)
    location_raw = _location_raw(candidate.required_location, context)
    repetition_raw = (
        _clamp01(candidate.repetition / config.repetition_saturation)
        if config.repetition_saturation > 0
        else _clamp01(float(candidate.repetition))
    )
    cooldown_raw = _cooldown_raw(candidate.last_activity_tick, context.now_tick, config)

    components = (
        AttentionComponent("stakes", stakes_raw, weights.stakes, stakes_raw * weights.stakes),
        AttentionComponent(
            "engagement", engagement_raw, weights.engagement, engagement_raw * weights.engagement
        ),
        AttentionComponent(
            "relationship",
            relationship_raw,
            weights.relationship,
            relationship_raw * weights.relationship,
        ),
        AttentionComponent(
            "deadline", deadline_raw, weights.deadline, deadline_raw * weights.deadline
        ),
        AttentionComponent(
            "location", location_raw, weights.location, location_raw * weights.location
        ),
        AttentionComponent(
            "repetition", repetition_raw, -weights.repetition, -(repetition_raw * weights.repetition)
        ),
        AttentionComponent(
            "cooldown", cooldown_raw, -weights.cooldown, -(cooldown_raw * weights.cooldown)
        ),
    )
    score = sum(component.contribution for component in components)
    reason_codes: list[str] = []
    if repetition_raw > 0.0:
        reason_codes.append(REASON_REPEATED)
    if cooldown_raw > 0.0:
        reason_codes.append(REASON_IN_COOLDOWN)
    return AttentionSelection(
        candidate=candidate,
        score=score,
        components=components,
        reason_codes=tuple(reason_codes),
        selected=False,
    )


def _snapshot_hash(
    candidates: Sequence[AttentionCandidate],
    context: AttentionContext,
    config: AttentionConfig,
) -> str:
    payload = {
        "config_version": config.version,
        "focus_limit": config.focus_limit,
        "owner_id": context.owner_id,
        "now_tick": context.now_tick,
        "sources": sorted(
            (candidate.candidate_id, candidate.source_ref, int(candidate.revision))
            for candidate in candidates
        ),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def rank_attention(
    candidates: Iterable[AttentionCandidate],
    context: AttentionContext,
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> AttentionDecision:
    """Filter, score, and bound the candidate set for a later director.

    Pure and deterministic: identical inputs, configuration and context always
    produce an identical order and identical reason data. Nothing is written,
    so unselected candidate state is preserved.
    """
    ordered_candidates = sorted(candidates, key=lambda candidate: candidate.candidate_id)
    eligible: list[AttentionCandidate] = []
    excluded: list[AttentionExclusion] = []
    for candidate in ordered_candidates:
        reasons = eligibility_reasons(candidate, context, config)
        if reasons:
            excluded.append(AttentionExclusion(candidate=candidate, reasons=reasons))
        else:
            eligible.append(candidate)

    scored = [score_candidate(candidate, context, config) for candidate in eligible]
    scored.sort(key=lambda selection: (-selection.score, selection.candidate.candidate_id))

    focus_limit = max(0, int(config.focus_limit))
    ranked: list[AttentionSelection] = []
    selected: list[AttentionSelection] = []
    for index, selection in enumerate(scored):
        is_selected = index < focus_limit
        codes = (REASON_SELECTED,) if is_selected else (REASON_BELOW_FOCUS_LIMIT,)
        reason_codes = tuple(selection.reason_codes) + codes
        final = AttentionSelection(
            candidate=selection.candidate,
            score=selection.score,
            components=selection.components,
            reason_codes=reason_codes,
            selected=is_selected,
        )
        ranked.append(final)
        if is_selected:
            selected.append(final)

    sources = tuple(
        AttentionSourceRef(
            candidate_id=candidate.candidate_id,
            source_ref=candidate.source_ref,
            revision=int(candidate.revision),
        )
        for candidate in ordered_candidates
    )

    counts: dict[str, int] = {}
    for exclusion in excluded:
        for reason in exclusion.reasons:
            counts[reason] = counts.get(reason, 0) + 1
    for selection in ranked:
        for reason in selection.reason_codes:
            counts[reason] = counts.get(reason, 0) + 1
    reason_counts = tuple(sorted(counts.items()))

    decision = AttentionDecision(
        config_version=config.version,
        owner_id=context.owner_id,
        now_tick=context.now_tick,
        focus_limit=focus_limit,
        selected=tuple(selected),
        ranked=tuple(ranked),
        excluded=tuple(excluded),
        sources=sources,
        snapshot_hash=_snapshot_hash(ordered_candidates, context, config),
        reason_counts=reason_counts,
    )
    log_info(
        "narrative_attention_ranked",
        context={
            "owner_id": context.owner_id,
            "config_version": config.version,
            "tick": context.now_tick,
            "candidate_count": len(ordered_candidates),
            "eligible_count": len(ranked),
            "selected_count": len(selected),
            "excluded_count": len(excluded),
            "focus_limit": focus_limit,
            "snapshot_hash": decision.snapshot_hash,
        },
    )
    return decision


def extract_engagement(
    owner_id: str,
    *,
    participants: Iterable[Any] = (),
    now_tick: int,
    window_ticks: int = DEFAULT_ENGAGEMENT_WINDOW_TICKS,
) -> EngagementSignals:
    """Count observable engagement evidence from durable records.

    Only owner actions count: initiated dialogue, sent correspondence, explicit
    clue questions and committed gameplay participation. Passive receipt
    (collection/reading) is counted separately and never scored.

    Engagement is counterpart-scoped: ``participants`` names the other parties
    of the candidate, and when it resolves to no other party the result is
    zeroed rather than falling back to the owner's global activity, which would
    otherwise attribute unrelated history to an owner-only candidate. The
    Committed-play counters are still candidate-window facts, not a claim
    that every counted occurrence belongs to this thread.
    """
    from world.narrative.models import DialogueTurn, LetterSend, LetterState, NarrativeEvent

    clean_owner = str(owner_id)
    targets = {str(participant) for participant in participants if str(participant) != clean_owner}
    if not targets:
        return EngagementSignals()
    start = int(now_tick) - max(0, int(window_ticks))

    initiations = 0
    clue_questions = 0
    for npc_id, speech in (
        DialogueTurn.objects.filter(
            player_id=clean_owner,
            kind="player",
            tick__gte=start,
            tick__lte=int(now_tick),
        )
        .order_by("id")
        .values_list("npc_id", "speech")
    ):
        if str(npc_id) not in targets:
            continue
        initiations += 1
        if "?" in (speech or "") or "？" in (speech or ""):
            clue_questions += 1

    sustained = (
        LetterSend.objects.filter(
            sender_id=clean_owner,
            recipient_id__in=sorted(targets),
            sent_tick__gte=start,
            sent_tick__lte=int(now_tick),
        )
        .order_by("pk")
        .count()
    )

    participation = 0
    passive_events = 0
    scanned = 0
    scan_truncated = False
    for event_type, members in (
        NarrativeEvent.objects.filter(tick__gte=start, tick__lte=int(now_tick))
        .order_by("pk")
        .values_list("event_type", "participants")
    ):
        scanned += 1
        if scanned > MAX_ENGAGEMENT_EVENTS:
            scan_truncated = True
            break
        if clean_owner not in {str(member) for member in (members or [])}:
            continue
        if event_type in PASSIVE_RECEIPT_EVENT_TYPES:
            passive_events += 1
        else:
            participation += 1
    if scan_truncated:
        log_warn(
            "narrative_attention_engagement_truncated",
            context={
                "owner_id": clean_owner,
                "scanned": scanned - 1,
                "tick": int(now_tick),
            },
        )

    passive_reads = (
        LetterState.objects.filter(
            recipient_id=clean_owner,
            read_tick__gte=start,
            read_tick__lte=int(now_tick),
        )
        .order_by("pk")
        .count()
    )

    return EngagementSignals(
        dialogue_initiations=initiations,
        sustained_correspondence=sustained,
        clue_questions=clue_questions,
        participation=participation,
        passive_receipts=passive_events + passive_reads,
    )


def collect_schedule_blocks(
    participant_ids: Iterable[Any], *, interaction_kind: str = "talk"
) -> frozenset[str]:
    """Return participant pks whose current schedule state blocks interaction.

    Non-player, resolvable NPC participants are checked through the schedule
    owner's ``interaction_reason``; anything else is never blocked.
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.npc_schedules import interaction_reason

    resolved: list[int] = []
    for participant in participant_ids:
        text = str(participant)
        if text.isdigit():
            resolved.append(int(text))
    blocked: set[str] = set()
    if not resolved:
        return frozenset()
    for obj in ObjectDB.objects.filter(pk__in=sorted(set(resolved))).order_by("pk"):
        if isinstance(obj, NPC) and interaction_reason(obj, interaction_kind) is not None:
            blocked.add(str(obj.pk))
    return frozenset(blocked)


def thread_required_location(thread: Any) -> str:
    """The location of the most recently linked event, or ``""`` when unknown.

    Links sharing a tick resolve by descending durable link id so the answer is
    deterministic; an event without a location never becomes the answer.
    """
    from world.narrative.models import NarrativeEvent

    links = thread.links.filter(source_kind="event").order_by("-created_tick", "-id")
    for link in links:
        event = (
            NarrativeEvent.objects.filter(source_id=link.source_ref)
            .only("location")
            .first()
        )
        if event is not None and event.location:
            return str(event.location)
    return ""


def collect_quest_deadlines(owner: Any) -> dict[str, int]:
    """Map in-progress linked quest ids to their earliest deadline tick."""
    from world.quests.runtime import QuestDataError, QuestState, read_records

    deadlines: dict[str, int] = {}
    try:
        records = read_records(owner)
    except QuestDataError as error:
        log_warn(
            "narrative_attention_quest_deadlines_unavailable",
            context={"owner_id": str(getattr(owner, "pk", owner))},
            exc=error,
        )
        return deadlines
    for record in records:
        if record.state is not QuestState.IN_PROGRESS or record.deadline_tick is None:
            continue
        existing = deadlines.get(record.quest_id)
        if existing is None or record.deadline_tick < existing:
            deadlines[record.quest_id] = int(record.deadline_tick)
    return deadlines


def _owner_memory_ids(owner_id: str) -> set[int]:
    from world.narrative.models import MemoryRecord

    return set(
        MemoryRecord.objects.filter(owner_id=owner_id)
        .order_by("id")
        .values_list("id", flat=True)
    )


def _dialogue_ref_belongs_to(ref: str, owner_id: str) -> bool:
    from world.narrative.models import DialogueTurn

    submission_id = ref.rsplit(":", 1)[0]
    return (
        DialogueTurn.objects.filter(submission_id=submission_id, player_id=owner_id)
        .order_by("pk")
        .exists()
    )


def _link_is_owner_experience(
    link: Any, owner_id: str, owner_memory_ids: set[int]
) -> bool:
    """Whether one durable thread link records the owner's own experience."""
    from world.narrative.models import LetterSend, NarrativeEvent

    kind = link.source_kind
    if kind == "memory":
        ref = str(link.source_ref)
        if ref.startswith("mem:") and ref[4:].isdigit():
            return int(ref[4:]) in owner_memory_ids
        return False
    if kind == "dialogue":
        return _dialogue_ref_belongs_to(str(link.source_ref), owner_id)
    if kind == "event":
        event = (
            NarrativeEvent.objects.filter(source_id=link.source_ref)
            .only("participants")
            .first()
        )
        return event is not None and owner_id in {
            str(member) for member in (event.participants or [])
        }
    if kind == "letter":
        letter = (
            LetterSend.objects.filter(source_id=link.source_ref)
            .only("sender_id", "recipient_id")
            .first()
        )
        return letter is not None and owner_id in (letter.sender_id, letter.recipient_id)
    return False


def _participant_relationship(owner: Any, participants: Iterable[Any]) -> int:
    """Max participant-NPC affinity toward the owner; 0 when none is known."""
    from evennia.objects.models import ObjectDB

    from typeclasses.npcs import NPC

    resolved: list[int] = []
    for participant in participants:
        text = str(participant)
        if text.isdigit():
            resolved.append(int(text))
    best = 0
    if not resolved:
        return best
    for obj in ObjectDB.objects.filter(pk__in=sorted(set(resolved))).order_by("pk"):
        if not isinstance(obj, NPC):
            continue
        try:
            value = int(obj.relations.affinity_for(owner))
        except Exception as error:  # pragma: no cover - defensive read guard
            log_warn(
                "narrative_attention_relationship_unavailable",
                context={"owner_id": str(getattr(owner, "pk", owner)), "npc": obj.pk},
                exc=error,
            )
            continue
        best = max(best, value)
    return best


def build_attention_candidates(
    *,
    owner: Any,
    now_tick: Optional[int] = None,
    owner_location: Optional[str] = None,
    reachable_locations: Iterable[str] = (),
    blocked_participants: Iterable[str] = (),
    window_ticks: int = DEFAULT_ENGAGEMENT_WINDOW_TICKS,
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> tuple[AttentionCandidate, ...]:
    """Read-only durable extraction of thread and confirmed-request candidates.

    Every active story thread and every valid confirmed request version of the
    owner becomes a plain candidate; eligibility is decided later by
    :func:`rank_attention`, so exclusions stay observable. Nothing is written.
    """
    from world.narrative.authoring import latest_confirmed_request
    from world.narrative.models import CreativeRequest, StoryThread
    from world.narrative.threads import thread_accessible

    owner_id = str(owner.pk)
    tick = int(now_tick) if now_tick is not None else _current_tick(owner)
    if owner_location is None:
        location = getattr(owner, "location", None)
        owner_location = str(location.pk) if location is not None else ""
    reachable = frozenset(str(item) for item in reachable_locations)

    owner_memory_ids = _owner_memory_ids(owner_id)
    quest_deadlines = collect_quest_deadlines(owner)
    latest_request = latest_confirmed_request(owner_id)

    threads = list(
        StoryThread.objects.filter(state="active").order_by("id")[: MAX_CONSIDERED_THREADS + 1]
    )
    if len(threads) > MAX_CONSIDERED_THREADS:
        truncated = (
            StoryThread.objects.filter(state="active").count() - MAX_CONSIDERED_THREADS
        )
        threads = threads[:MAX_CONSIDERED_THREADS]
        log_warn(
            "narrative_attention_candidates_truncated",
            context={
                "owner_id": owner_id,
                "truncated_count": truncated,
                "considered": MAX_CONSIDERED_THREADS,
                "tick": tick,
            },
        )

    blocked = frozenset(str(item) for item in blocked_participants)
    candidates: list[AttentionCandidate] = []
    for thread in threads:
        links = list(thread.links.order_by("id"))
        accessible = thread_accessible(thread, owner_id)
        is_participant = owner_id in {str(item) for item in (thread.participants or [])}
        own_experience = any(
            _link_is_owner_experience(link, owner_id, owner_memory_ids) for link in links
        )
        known = accessible or is_participant or own_experience
        invested = is_participant or own_experience
        cadence = [int(thread.created_tick)]
        cadence.extend(int(tick_value) for tick_value in (thread.development_ticks or []))
        cadence.extend(int(link.created_tick) for link in links)
        deadline: Optional[int] = None
        for link in links:
            if link.source_kind != "quest":
                continue
            candidate_deadline = quest_deadlines.get(str(link.source_ref))
            if candidate_deadline is None:
                continue
            deadline = (
                candidate_deadline if deadline is None else min(deadline, candidate_deadline)
            )
        others = tuple(
            str(item) for item in (thread.participants or []) if str(item) != owner_id
        )
        candidates.append(
            AttentionCandidate(
                candidate_id=f"thread:{thread.thread_id}",
                source_kind=SOURCE_THREAD,
                source_ref=str(thread.thread_id),
                revision=int(thread.revision),
                origin=str(thread.origin),
                participants=tuple(
                    str(item) for item in (thread.participants or [])
                ),
                invested=invested,
                confirmed=False,
                knowledge=known,
                authoritative=True,
                required_location=thread_required_location(thread),
                capability="dialogue",
                unresolved_stakes=len(thread.unresolved_questions or [])
                + len(thread.commitments or []),
                relationship=_participant_relationship(owner, others),
                deadline_tick=deadline,
                engagement=extract_engagement(
                    owner_id,
                    participants=others,
                    now_tick=tick,
                    window_ticks=window_ticks,
                ),
                repetition=max(0, len(thread.development_ticks or []) - 1),
                last_activity_tick=max(cadence) if cadence else None,
                salience=0,
            )
        )

    for request in (
        CreativeRequest.objects.filter(owner_id=owner_id).order_by("id")
    ):
        valid = str(request.validation_status) == "valid"
        candidates.append(
            AttentionCandidate(
                candidate_id=f"request:{request.submission_key}",
                source_kind=SOURCE_REQUEST,
                source_ref=str(request.submission_key),
                revision=int(request.version),
                origin="confirmed_request",
                participants=(owner_id,),
                invested=False,
                confirmed=valid,
                knowledge=True,
                authoritative=bool(latest_request is not None and request.pk == latest_request.pk),
                required_location="",
                capability="quest",
                unresolved_stakes=0,
                relationship=0,
                deadline_tick=None,
                engagement=EngagementSignals(),
                repetition=0,
                last_activity_tick=int(request.submitted_tick),
                salience=0,
            )
        )

    return tuple(candidates)


def _current_tick(owner: Any) -> int:
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return int(clock.tick) if clock is not None else 0


def build_context(
    *,
    owner: Any,
    now_tick: Optional[int] = None,
    owner_location: Optional[str] = None,
    reachable_locations: Iterable[str] = (),
    interaction_kind: str = "talk",
) -> AttentionContext:
    """Assemble the owner-side eligibility context from durable read-only state."""
    owner_id = str(owner.pk)
    tick = int(now_tick) if now_tick is not None else _current_tick(owner)
    if owner_location is None:
        location = getattr(owner, "location", None)
        owner_location = str(location.pk) if location is not None else ""
    reachable = frozenset(str(item) for item in reachable_locations) | {owner_location}
    return AttentionContext(
        owner_id=owner_id,
        now_tick=tick,
        owner_location=owner_location,
        reachable_locations=reachable,
        blocked_participants=collect_schedule_blocks(
            _thread_participants(owner_id), interaction_kind=interaction_kind
        ),
    )


def _thread_participants(owner_id: str) -> list[str]:
    from world.narrative.models import StoryThread

    participants: set[str] = set()
    for members in (
        StoryThread.objects.filter(state="active")
        .order_by("id")[:MAX_CONSIDERED_THREADS]
        .values_list("participants", flat=True)
    ):
        for member in members or []:
            text = str(member)
            if text != owner_id:
                participants.add(text)
    return sorted(participants)


def attention_snapshot(
    candidates: Iterable[AttentionCandidate],
    context: AttentionContext,
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> Mapping[str, Any]:
    """The plain snapshot reference bundle a director can persist alongside a beat."""
    ordered = sorted(candidates, key=lambda candidate: candidate.candidate_id)
    return {
        "config_version": config.version,
        "owner_id": context.owner_id,
        "now_tick": context.now_tick,
        "sources": tuple(
            AttentionSourceRef(
                candidate_id=candidate.candidate_id,
                source_ref=candidate.source_ref,
                revision=int(candidate.revision),
            )
            for candidate in ordered
        ),
        "snapshot_hash": _snapshot_hash(ordered, context, config),
    }
