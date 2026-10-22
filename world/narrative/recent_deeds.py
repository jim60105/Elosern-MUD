"""Authorized recent-deed selection and bounded rendering for epithet nomination.

OpenSpec change: select-authorized-recent-deeds
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5, §5.1, §6, §9, §10
Specs: openspec/specs/title-system/spec.md

Producer metadata contract: every supported producer persists its settlement
location reference in the fact content as ``"location": {"id": <durable
identity>, "label": <readable label at settlement>}``; both are empty when the
producer held no authoritative location. Selection reads only that snapshot —
never a live room, quest registry or clock — and renders each retained fact's
own ``tick`` and ``location`` plus, for a compressed repetition run, one
source-linked ``occurrences`` reference per occurrence so differing times and
places are never misattributed.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Sequence

from django.db.models import QuerySet

from world.narrative.adult_projection import project_adult_action_for_recipient
from world.narrative.events import LOCATION_LABEL_MAX_CHARS, LocationSnapshot
from world.narrative.models import NarrativeEvent
from world.observability import log_warn
from world.rules.clock import CLOCK_YAML

#: Maximum Unicode code points allowed for rendered recent deeds JSON envelope
RECENT_DEEDS_JSON_CODE_POINTS_LIMIT = 8000

#: Maximum number of factual groups retained in the nomination feed
RECENT_DEEDS_MAX_GROUPS = 8

#: Closed deterministic narrative event types admitted for recent-deed nomination
ADMITTED_EVENT_TYPES = frozenset({
    "quest_completion",
    "guild_exam_settlement",
    "combat_encounter",
    "skill_use",
    "adult_action",
    "adult_milestone",
})

#: Excluded event types (explicit non-evidence)
EXCLUDED_EVENT_TYPES = frozenset({
    "encounter_protection",
    "claim_receipt",
    "narrative_beat",
    "correspondence_delivery",
    "correspondence_read",
    "wilderness_move",
})


def canonical_two_day_seconds() -> int:
    """Derive canonical two-day world window duration in seconds from clock config."""
    seconds_per_hour = int(CLOCK_YAML.get("seconds_per_hour", 3600))
    hours_per_day = int(CLOCK_YAML.get("hours_per_day", 24))
    day_seconds = seconds_per_hour * hours_per_day
    return 2 * day_seconds


def compute_recent_deeds_window(frozen_tick: int) -> tuple[int, int]:
    """Compute the inclusive world tick window [lower_bound, upper_bound].

    Upper bound is T (frozen_tick).
    Lower bound is max(0, T - 2 canonical world days).
    """
    t = int(frozen_tick)
    duration = canonical_two_day_seconds()
    lower_bound = max(0, t - duration)
    return lower_bound, t


def _durable_pk(entity: Any) -> str:
    """Return stable string identifier for an entity."""
    pk = getattr(entity, "pk", None)
    if pk is not None:
        return str(pk)
    entity_id = getattr(entity, "id", None)
    if entity_id is not None:
        return str(entity_id)
    key = getattr(entity, "key", None)
    if key is not None and str(key).strip():
        return str(key).strip()
    return str(entity).strip()


@dataclass(frozen=True)
class AuthorizedDeedRecord:
    """A single authorized, validated, projected narrative deed record."""

    source_id: str
    event_type: str
    tick: int
    data: dict[str, Any]
    award_results: tuple[dict[str, Any], ...] = ()
    location: LocationSnapshot = LocationSnapshot()


@dataclass
class DeedFactGroup:
    """A bounded factual group of one or more related recent occurrences."""

    group_type: str
    latest_tick: int
    source_ids: list[str]
    count: int
    facts: dict[str, Any]

    @property
    def primary_source_id(self) -> str:
        return self.source_ids[0] if self.source_ids else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_type": self.group_type,
            "latest_tick": self.latest_tick,
            "source_ids": list(self.source_ids),
            "count": self.count,
            "facts": self.facts,
        }


@dataclass(frozen=True)
class RecentDeedsSelectionResult:
    """Immutable result of recent-deed selection and bounded JSON rendering."""

    player_id: str
    frozen_tick: int
    groups: tuple[DeedFactGroup, ...]
    source_ids: tuple[str, ...]
    rendered_json: str


def _record_location(content: dict[str, Any], source_id: str) -> LocationSnapshot:
    """Read the settlement-time location reference of one committed occurrence.

    The producer's snapshot is the only authority: a supported record always
    carries the key (an empty identity states unknown explicitly), so an absent
    or malformed snapshot is unsupported evidence and fails closed for that
    record. No live room and no stored column value is ever substituted for a
    missing snapshot.
    """
    raw = content.get("location")
    if not isinstance(raw, dict) or set(raw) - {"id", "label"}:
        raise ValueError(f"malformed location snapshot in {source_id}")
    identity = raw.get("id")
    label = raw.get("label", "")
    if (
        not isinstance(identity, str)
        or not isinstance(label, str)
        or (not identity and label)
    ):
        raise ValueError(f"malformed location snapshot in {source_id}")
    return LocationSnapshot(
        identity=identity,
        label=label[:LOCATION_LABEL_MAX_CHARS],
    )


def _authorized_record(
    event: NarrativeEvent,
    event_type: str,
    data: dict[str, Any],
    award_results: list[dict[str, Any]],
    location: LocationSnapshot,
) -> AuthorizedDeedRecord:
    """Build one authorized record whose facts state their own time and place."""
    facts = dict(data)
    facts["tick"] = int(event.tick)
    facts["location"] = location.to_json()
    return AuthorizedDeedRecord(
        source_id=event.source_id,
        event_type=event_type,
        tick=int(event.tick),
        data=facts,
        award_results=tuple(award_results),
        location=location,
    )


def _validate_and_project_record(
    event: NarrativeEvent,
    player_pk: str,
) -> AuthorizedDeedRecord | None:
    """Validate and project a single narrative event for player_pk.

    Returns AuthorizedDeedRecord if authorized and valid, or None if omitted/inaccessible.
    Raises ValueError on malformed eligible record.
    """
    event_type = str(event.event_type)
    if event_type not in ADMITTED_EVENT_TYPES:
        return None

    # Exclude model-authored statements, routine activities, protection
    if event_type in EXCLUDED_EVENT_TYPES:
        return None

    participants = [str(p) for p in (event.participants or ())]
    if player_pk not in participants:
        return None

    content = event.content if isinstance(event.content, dict) else {}
    location = _record_location(content, str(event.source_id))

    raw_awards = content.get("award_results", [])
    award_results: list[dict[str, Any]] = []
    if isinstance(raw_awards, list):
        award_results = [dict(a) for a in raw_awards if isinstance(a, dict)]

    if event_type == "quest_completion":
        quest_id = content.get("quest_id")
        definition_key = content.get("definition_key")
        completed_objective = content.get("completed_objective")
        outcome = content.get("outcome")
        if not (quest_id and definition_key and completed_objective is not None and outcome):
            raise ValueError(f"malformed quest_completion record {event.source_id}")
        data = {
            "quest_id": str(quest_id),
            "definition_key": str(definition_key),
            "completed_objective": dict(completed_objective) if isinstance(completed_objective, dict) else str(completed_objective),
            "outcome": str(outcome),
        }
        return _authorized_record(
            event, event_type, data, award_results, location
        )

    elif event_type == "guild_exam_settlement":
        passed = content.get("passed")
        if not passed:
            # Only passed exams are admitted evidence
            return None
        if not isinstance(passed, bool):
            raise ValueError(f"malformed guild_exam_settlement passed value {passed!r} in {event.source_id}")
        exam_id = content.get("exam_id")
        attained_rank = content.get("attained_rank")
        if not (exam_id and attained_rank):
            raise ValueError(f"malformed guild_exam_settlement record {event.source_id}")
        data = {
            "exam_id": str(exam_id),
            "target_rank": str(content.get("target_rank", "")),
            "attained_rank": str(attained_rank),
            "passed": True,
        }
        return _authorized_record(
            event, event_type, data, award_results, location
        )

    elif event_type == "combat_encounter":
        encounter_id = content.get("encounter_id")
        session_id = content.get("session_id")
        outcome = content.get("outcome")
        if not (encounter_id and outcome):
            raise ValueError(f"malformed combat_encounter record {event.source_id}")
        data = {
            "encounter_id": str(encounter_id),
            # The transport token is reusable and diagnostic only: two
            # engagements can share it, so it never keys this record.
            "session_id": str(session_id or ""),
            "outcome": str(outcome),
            "gameplay_outcome": str(content.get("gameplay_outcome", outcome)),
            "mode": str(content.get("mode", "hostile")),
            "participant_ids": [str(pid) for pid in content.get("participant_ids", [])],
            "opponent_ids": [str(oid) for oid in content.get("opponent_ids", [])],
            "rounds_elapsed": int(content.get("rounds_elapsed", 0)),
            "display_snapshots": dict(content.get("display_snapshots", {})),
        }
        return _authorized_record(
            event, event_type, data, award_results, location
        )

    elif event_type == "skill_use":
        skill_key = content.get("skill_key")
        actor = content.get("actor")
        if not (skill_key and isinstance(actor, dict)):
            raise ValueError(f"malformed skill_use record {event.source_id}")
        actor_id = str(actor.get("id", ""))
        recipients = content.get("recipients", [])
        recip_records = [
            {"id": str(r.get("id", "")), "name": str(r.get("name", "")), "role": "recipient"}
            for r in recipients
            if isinstance(r, dict)
        ]
        # In combat or outside, personal involvement means player is actor or recipient
        if actor_id != player_pk and not any(r["id"] == player_pk for r in recip_records):
            return None

        data = {
            "action_source_id": str(content.get("action_source_id", event.source_id)),
            "skill_key": str(skill_key),
            "skill_name": str(content.get("skill_name", skill_key)),
            "category": str(content.get("category", "skill")),
            "encounter_context": content.get("encounter_context"),
            "actor": {"id": actor_id, "name": str(actor.get("name", "")), "role": "actor"},
            "recipients": recip_records,
            "effects": [dict(e) for e in content.get("effects", []) if isinstance(e, dict)],
            "claim_limits": {
                "rescue_claimed": False,
                "protection_claimed": False,
                "exceptional_difficulty": False,
            },
        }
        return _authorized_record(
            event, event_type, data, award_results, location
        )

    elif event_type == "adult_action":
        projected = project_adult_action_for_recipient(
            event.content,
            recipient_pk=player_pk,
            source_id=event.source_id,
        )
        if projected is None:
            # Not authorized or malformed permission block
            return None
        return _authorized_record(
            event, event_type, projected, award_results, location
        )

    elif event_type == "adult_milestone":
        # Adult milestone records are private to their entity
        entity_id = str(content.get("entity_id", ""))
        if entity_id != player_pk:
            return None
        milestone_kind = content.get("milestone_kind")
        identifier = content.get("identifier")
        if not (milestone_kind and identifier):
            raise ValueError(f"malformed adult_milestone record {event.source_id}")
        data = {
            "action_source_id": str(content.get("action_source_id", "")),
            "milestone_kind": str(milestone_kind),
            "identifier": str(identifier),
            "entity_id": player_pk,
            "entity_name": str(content.get("entity_name", "")),
            "details": dict(content.get("details", {})) if isinstance(content.get("details"), dict) else {},
            "encounter_context": content.get("encounter_context"),
            "privacy": {
                "private_experience": True,
                "public_notoriety": False,
            },
        }
        return _authorized_record(
            event, event_type, data, award_results, location
        )

    return None


def _load_authorized_records(
    player_pk: str,
    lower_bound: int,
    upper_bound: int,
    frozen_tick: int,
) -> list[AuthorizedDeedRecord]:
    """Query durable storage and project authorized records within the frozen window.

    Malformed eligible records fail closed for that record only with a diagnostic
    warning; the warning carries the admitted window's frozen tick so it
    correlates with admission and failure diagnostics.
    """
    qs: QuerySet[NarrativeEvent] = NarrativeEvent.objects.filter(
        tick__gte=lower_bound,
        tick__lte=upper_bound,
        event_type__in=list(ADMITTED_EVENT_TYPES),
    ).order_by("tick", "source_id")

    authorized_records: list[AuthorizedDeedRecord] = []
    seen_sources: set[str] = set()

    for event in qs:
        if event.source_id in seen_sources:
            continue
        try:
            record = _validate_and_project_record(event, player_pk)
            if record is not None:
                seen_sources.add(record.source_id)
                authorized_records.append(record)
        except Exception as error:
            # Privacy-safe diagnostic warning: IDs and event_type only, never raw payload
            log_warn(
                "recent_deed_record_malformed",
                exc=error,
                context={
                    "source_id": str(event.source_id),
                    "event_type": str(event.event_type),
                    "frozen_tick": int(frozen_tick),
                },
            )
            continue

    return authorized_records


def _milestone_encounter_id(record: AuthorizedDeedRecord) -> str:
    """Return the encounter occurrence one milestone was committed under, or ``""``."""
    encounter_context = record.data.get("encounter_context")
    if not isinstance(encounter_context, dict):
        return ""
    return str(encounter_context.get("encounter_id", "") or "")


def _get_action_compression_key(record: AuthorizedDeedRecord) -> tuple[str, str, str, str, str] | None:
    """Return stable grouping tuple for consecutive action compression:

    (action_type, actor_id, sorted_recipients_str, encounter_id, player_role)

    The encounter component is the unique engagement occurrence, never the
    reusable transport session token: two engagements sharing one token can
    never compress into the same run.
    """
    if record.event_type not in ("skill_use", "adult_action"):
        return None

    data = record.data
    action_type = str(data.get("skill_key") or data.get("act_key") or "")
    actor_id = str(data.get("actor", {}).get("id", ""))
    recips = data.get("recipients", [])
    recip_ids = sorted(str(r.get("id", "")) for r in recips if isinstance(r, dict))
    recip_key = ",".join(recip_ids)

    enc_ctx = data.get("encounter_context")
    enc_encounter = str(enc_ctx.get("encounter_id", "")) if isinstance(enc_ctx, dict) else ""

    player_role = "actor" if actor_id == data.get("player_id") else "recipient"

    return (action_type, actor_id, recip_key, enc_encounter, player_role)


def _occurrence_context(
    records: Sequence[AuthorizedDeedRecord],
) -> list[dict[str, Any]]:
    """Return one source-linked time/location reference per compressed occurrence.

    Compression keeps every occurrence's own committed time and location, so a
    later occurrence's tick is never folded into an earlier fact and no
    occurrence is given the run's first location. A single occurrence needs no
    list: its fact already carries its own tick and location.
    """
    if len(records) < 2:
        return []
    return [
        {
            "source_id": record.source_id,
            "tick": record.tick,
            "location": record.location.to_json(),
        }
        for record in records
    ]


def _build_compressed_action_fact(
    records: list[AuthorizedDeedRecord],
    milestones: list[AuthorizedDeedRecord],
) -> dict[str, Any]:
    """Build factual content for a run of consecutive compressed actions."""
    first = records[0]
    base_data = dict(first.data)
    is_adult = first.event_type == "adult_action"

    # Collect distinct results
    distinct_effects: list[dict[str, Any]] = []
    seen_effects: set[str] = set()

    for r in records:
        effs = r.data.get("effects") or r.data.get("outcomes", {}).get("effects", [])
        if isinstance(effs, list):
            for e in effs:
                if isinstance(e, dict):
                    e_json = json.dumps(e, sort_keys=True)
                    if e_json not in seen_effects:
                        seen_effects.add(e_json)
                        distinct_effects.append(e)

    def _distinct_rows(family: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in records:
            raw_rows = record.data.get("outcomes", {}).get(family, [])
            if not isinstance(raw_rows, list):
                continue
            for row in raw_rows:
                if isinstance(row, dict):
                    row_json = json.dumps(row, sort_keys=True)
                    if row_json not in seen:
                        seen.add(row_json)
                        rows.append(row)
        return rows

    # Collect distinct resistance, transition and counter results across the
    # whole run: a result present only in a later occurrence is not lost.
    distinct_resist = _distinct_rows("resistance")
    distinct_transitions = _distinct_rows("transitions")
    distinct_counters = _distinct_rows("counters")

    # Collect distinct milestones keyed by their immutable source identity. An
    # embedded summary is the same occurrence as its authorized milestone row,
    # so the richer authorized record replaces it in place: the occurrence
    # keeps its own committed tick and location instead of the action's.
    combined_milestones: dict[str, dict[str, Any]] = {}
    for r in records:
        for ms in r.data.get("milestones", []):
            if isinstance(ms, dict):
                ms_id = str(
                    ms.get("source_id")
                    or f"{ms.get('milestone_kind')}:{ms.get('identifier')}"
                )
                combined_milestones.setdefault(ms_id, ms)

    for ms_rec in milestones:
        combined_milestones[ms_rec.source_id] = {
            "source_id": ms_rec.source_id,
            "milestone_kind": ms_rec.data.get("milestone_kind"),
            "identifier": ms_rec.data.get("identifier"),
            "details": ms_rec.data.get("details"),
            "tick": ms_rec.tick,
            "location": ms_rec.location.to_json(),
        }

    milestone_rows = list(combined_milestones.values())

    if is_adult:
        outcomes = dict(base_data.get("outcomes", {}))
        outcomes["effects"] = distinct_effects
        outcomes["resistance"] = distinct_resist
        outcomes["transitions"] = distinct_transitions
        outcomes["counters"] = distinct_counters
        base_data["outcomes"] = outcomes
        base_data["milestones"] = milestone_rows
    else:
        base_data["effects"] = distinct_effects
        base_data["milestones"] = milestone_rows

    # A compressed run keeps every occurrence's own time and location.
    occurrences = _occurrence_context(records)
    if occurrences:
        base_data["occurrences"] = occurrences

    return base_data


def _group_and_aggregate_deeds(
    authorized_records: list[AuthorizedDeedRecord],
    player_pk: str,
) -> list[DeedFactGroup]:
    """Perform order-independent linking, consecutive action compression, and encounter grouping.

    Invariants:
    - Encounters group their terminal outcome with member combat actions.
    - A milestone records the encounter it was committed under, so an upkeep
      milestone with no admitted action of its own still joins that encounter.
    - An action and its milestones combine, counting that occurrence once.
    - Standalone milestones retain distinct factual representation.
    - Repetition compression applies to consecutive eligible actions matching
      action type, participants, roles, and encounter context.
    - Encounter identity is the unique engagement occurrence; the reusable
      transport session token neither joins nor merges anything.
    - Different encounters never merge.
    - Every group retains immutable source IDs without inventing aggregate IDs.
    """
    if not authorized_records:
        return []

    # Chronological sort for stream processing
    sorted_stream = sorted(authorized_records, key=lambda r: (r.tick, r.source_id))

    # 1. Index standalone milestones and combat encounter outcomes
    encounter_records: dict[str, AuthorizedDeedRecord] = {}
    action_records_by_source: dict[str, AuthorizedDeedRecord] = {}
    milestones_by_action_source: dict[str, list[AuthorizedDeedRecord]] = {}
    milestones_by_encounter: dict[str, list[AuthorizedDeedRecord]] = {}
    standalone_milestones: list[AuthorizedDeedRecord] = []

    for r in sorted_stream:
        if r.event_type == "combat_encounter":
            encounter_id = str(r.data.get("encounter_id", ""))
            if encounter_id:
                encounter_records[encounter_id] = r
        elif r.event_type in ("skill_use", "adult_action"):
            action_source_id = str(r.data.get("action_source_id") or r.source_id)
            action_records_by_source[action_source_id] = r

    # 1a. Attach every milestone to the occurrence it belongs to. A milestone
    # whose action was admitted belongs to that action; an upkeep milestone
    # names its own encounter (the boundary commits the milestone, never an
    # action) and joins that encounter's outcome directly; anything else is an
    # independent fact that keeps acting as an ordinary boundary.
    for r in sorted_stream:
        if r.event_type != "adult_milestone":
            continue
        action_src = str(r.data.get("action_source_id", ""))
        if action_src and action_src in action_records_by_source:
            milestones_by_action_source.setdefault(action_src, []).append(r)
            continue
        encounter_id = _milestone_encounter_id(r)
        if encounter_id and encounter_id in encounter_records:
            milestones_by_encounter.setdefault(encounter_id, []).append(r)
            continue
        standalone_milestones.append(r)

    # Milestones joined to an admitted action belong to that occurrence, so they
    # are not independent occurrences: they neither break a repetition run nor
    # form a group of their own. A milestone whose action was not admitted stays
    # standalone and keeps acting as an ordinary boundary.
    joined_milestone_sources: set[str] = {
        ms.source_id
        for ms_list in milestones_by_action_source.values()
        for ms in ms_list
    }
    joined_milestone_sources.update(
        ms.source_id
        for ms_list in milestones_by_encounter.values()
        for ms in ms_list
    )

    # 2. Identify consecutive action runs across the chronological action stream
    # A run breaks if action type, actor, recipients, encounter, or role changes.
    action_runs: list[list[AuthorizedDeedRecord]] = []
    current_run: list[AuthorizedDeedRecord] = []
    current_key: tuple[str, str, str, str, str] | None = None

    for r in sorted_stream:
        if (
            r.event_type == "adult_milestone"
            and r.source_id in joined_milestone_sources
        ):
            # Attached before compression: this occurrence's own result joins
            # its action later, through that action's run.
            continue
        if r.event_type not in ("skill_use", "adult_action"):
            # Non-action record breaks consecutive action run!
            if current_run:
                action_runs.append(current_run)
                current_run = []
                current_key = None
            continue

        r_key = _get_action_compression_key(r)
        if current_run and r_key == current_key:
            current_run.append(r)
        else:
            if current_run:
                action_runs.append(current_run)
            current_run = [r]
            current_key = r_key

    if current_run:
        action_runs.append(current_run)

    # 3. Associate action runs to combat encounters or standalone groups
    # Encounter occurrence id -> list of action runs
    encounter_action_runs: dict[str, list[list[AuthorizedDeedRecord]]] = {}
    standalone_action_runs: list[list[AuthorizedDeedRecord]] = []

    for run in action_runs:
        enc_ctx = run[0].data.get("encounter_context")
        encounter_id = str(enc_ctx.get("encounter_id", "")) if isinstance(enc_ctx, dict) else ""
        if encounter_id and encounter_id in encounter_records:
            encounter_action_runs.setdefault(encounter_id, []).append(run)
        else:
            standalone_action_runs.append(run)

    groups: list[DeedFactGroup] = []

    # 4. Form groups for Quest Completions
    for r in sorted_stream:
        if r.event_type == "quest_completion":
            groups.append(DeedFactGroup(
                group_type="quest_completion",
                latest_tick=r.tick,
                source_ids=[r.source_id],
                count=1,
                facts=dict(r.data),
            ))

    # 5. Form groups for Passed Guild Exams
    for r in sorted_stream:
        if r.event_type == "guild_exam_settlement":
            groups.append(DeedFactGroup(
                group_type="guild_exam_settlement",
                latest_tick=r.tick,
                source_ids=[r.source_id],
                count=1,
                facts=dict(r.data),
            ))

    # 6. Form groups for Combat Encounters (group encounter outcome + its action runs)
    for encounter_id, enc_record in encounter_records.items():
        all_enc_sources = [enc_record.source_id]
        runs = encounter_action_runs.get(encounter_id, [])
        all_ticks = [enc_record.tick]
        enc_facts = dict(enc_record.data)

        action_summaries = []
        for run in runs:
            run_sources = [r.source_id for r in run]
            all_enc_sources.extend(run_sources)
            all_ticks.extend(r.tick for r in run)

            # Milestones for actions in this run
            run_ms: list[AuthorizedDeedRecord] = []
            for r in run:
                action_src = str(r.data.get("action_source_id") or r.source_id)
                matched_ms = milestones_by_action_source.get(action_src, [])
                for ms in matched_ms:
                    if ms.source_id not in all_enc_sources:
                        all_enc_sources.append(ms.source_id)
                        all_ticks.append(ms.tick)
                        run_ms.append(ms)

            run_fact = _build_compressed_action_fact(run, run_ms)
            action_summaries.append({
                "action_type": run_fact.get("skill_key") or run_fact.get("act_key"),
                "count": len(run),
                "latest_tick": max(r.tick for r in run),
                "facts": run_fact,
            })

        if action_summaries:
            enc_facts["actions"] = action_summaries

        # Milestones this encounter owns directly (an upkeep boundary's
        # transitions) retain their own sources and facts in the same group.
        encounter_milestones = [
            {
                "source_id": ms.source_id,
                "milestone_kind": ms.data.get("milestone_kind"),
                "identifier": ms.data.get("identifier"),
                "details": ms.data.get("details"),
                "tick": ms.tick,
                "location": ms.location.to_json(),
            }
            for ms in milestones_by_encounter.get(encounter_id, ())
            if ms.source_id not in all_enc_sources
        ]
        for ms in milestones_by_encounter.get(encounter_id, ()):
            if ms.source_id not in all_enc_sources:
                all_enc_sources.append(ms.source_id)
                all_ticks.append(ms.tick)
        if encounter_milestones:
            enc_facts["milestones"] = encounter_milestones

        groups.append(DeedFactGroup(
            group_type="combat_encounter",
            latest_tick=max(all_ticks),
            source_ids=sorted(set(all_enc_sources)),
            count=1,
            facts=enc_facts,
        ))

    # 7. Form groups for Standalone Action Runs (outside combat or in unmatched encounters)
    for run in standalone_action_runs:
        run_sources: list[str] = [r.source_id for r in run]
        run_ticks: list[int] = [r.tick for r in run]
        run_ms: list[AuthorizedDeedRecord] = []

        for r in run:
            action_src = str(r.data.get("action_source_id") or r.source_id)
            matched_ms = milestones_by_action_source.get(action_src, [])
            for ms in matched_ms:
                if ms.source_id not in run_sources:
                    run_sources.append(ms.source_id)
                    run_ticks.append(ms.tick)
                    run_ms.append(ms)

        fact = _build_compressed_action_fact(run, run_ms)
        group_type = run[0].event_type

        groups.append(DeedFactGroup(
            group_type=group_type,
            latest_tick=max(run_ticks),
            source_ids=sorted(set(run_sources)),
            count=len(run),
            facts=fact,
        ))

    # 8. Form groups for Standalone Adult Milestones
    for ms in standalone_milestones:
        groups.append(DeedFactGroup(
            group_type="adult_milestone",
            latest_tick=ms.tick,
            source_ids=[ms.source_id],
            count=1,
            facts=dict(ms.data),
        ))

    return groups


def _render_envelope(groups: Sequence[DeedFactGroup]) -> str:
    """Serialize groups into the canonical JSON envelope string."""
    payload = {
        "recent_deeds": [g.to_dict() for g in groups],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _budget_and_render_groups(
    groups: list[DeedFactGroup],
) -> tuple[tuple[DeedFactGroup, ...], tuple[str, ...], str]:
    """Apply ordering, eight-group limit, oversized singleton omission, and 8000 code-point budget.

    Ordering rule:
    - `latest_tick` descending.
    - Tie-break: `primary_source_id` ascending.

    Budgeting rule:
    - Omit any individual group that cannot fit alone in 8000 code points.
    - Select at most 8 newest groups.
    - If combined envelope > 8000 code points, iteratively pop the oldest group.
    - If all groups omitted, return empty envelope `{"recent_deeds":[]}`.
    - Returned `groups`, `source_ids`, and `rendered_json` are completely synchronized.
    """
    if not groups:
        empty_json = _render_envelope([])
        return (), (), empty_json

    # Filter out oversized singletons immediately
    viable_groups: list[DeedFactGroup] = []
    for g in groups:
        single_json = _render_envelope([g])
        if len(single_json) <= RECENT_DEEDS_JSON_CODE_POINTS_LIMIT:
            viable_groups.append(g)

    if not viable_groups:
        empty_json = _render_envelope([])
        return (), (), empty_json

    # Sort newest first, tie-break by primary_source_id ascending
    viable_groups.sort(key=lambda g: (-g.latest_tick, g.primary_source_id))

    # Take at most RECENT_DEEDS_MAX_GROUPS (8)
    selected = viable_groups[:RECENT_DEEDS_MAX_GROUPS]

    # Iteratively drop the oldest group if over the 8000 code points limit
    rendered = _render_envelope(selected)
    while len(rendered) > RECENT_DEEDS_JSON_CODE_POINTS_LIMIT and selected:
        selected.pop()  # Drop oldest (last in descending list)
        rendered = _render_envelope(selected)

    final_groups = tuple(selected)
    # Collect all retained source_ids
    all_sources: list[str] = []
    for g in final_groups:
        all_sources.extend(g.source_ids)
    final_sources = tuple(sorted(set(all_sources)))

    return final_groups, final_sources, rendered


def select_authorized_recent_deeds(
    entity: Any,
    *,
    frozen_tick: int,
) -> RecentDeedsSelectionResult:
    """Select, authorize, aggregate and render recent deeds for a player character.

    Selection never consumes deeds, permitting subsequent requests to reuse them.
    The caller freezes world tick T once at admission and passes it here: the
    selector never reads a clock, so a late caller can never widen or shift the
    admitted window after generation or persistence.
    """
    player_pk = _durable_pk(entity)
    frozen_tick = int(frozen_tick)

    lower_bound, upper_bound = compute_recent_deeds_window(frozen_tick)

    authorized_records = _load_authorized_records(
        player_pk, lower_bound, upper_bound, frozen_tick
    )
    groups = _group_and_aggregate_deeds(authorized_records, player_pk)
    final_groups, final_sources, rendered_json = _budget_and_render_groups(groups)

    return RecentDeedsSelectionResult(
        player_id=player_pk,
        frozen_tick=frozen_tick,
        groups=final_groups,
        source_ids=final_sources,
        rendered_json=rendered_json,
    )
