"""Deterministic narrative event and milestone adapters for settled actions.

OpenSpec change: record-action-adult-recent-deeds
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5, §5.1, §5.2, §6, §10

Payload contracts:
1. Settled skill use (event_type="skill_use"):
   - action_source_id (str): Stable occurrence identity.
   - skill_key (str): Registered skill key.
   - skill_name (str): Display snapshot label.
   - category (str): Skill taxonomy category.
   - encounter_context (dict | None): Context if in combat (session_id, round_number).
   - actor (dict): Actual actor ID, name, and role="actor".
   - recipients (list[dict]): Explicit list of actual targets who received effects.
   - effects (list[dict]): Concrete committed effects (damage, heal, buffs).
   - claim_limits (dict): Inviolable bounds (rescue_claimed=False, protection_claimed=False).
   - award_results (list[dict]): Finalized automatic built-in-title awards.

2. Adult action (event_type="adult_action"):
   - Same provenance, actor, recipients, and award_results as above.
   - outcomes (dict): Structured outcomes including transitions, counters, resistance, and effects.
   - milestones (list[dict]): Summaries of newly crossed milestones with stable provenance.
   - visibility (str): "private" (no external observers) or "public" (third-party audience present).
   - privacy (dict): Bounds forbidding consent/willingness/relationship inference.
   - field_access (dict): Authorization-ready field knowability per participant.

3. Adult milestone (event_type="adult_milestone"):
   - action_source_id (str): Provocateur action occurrence identity.
   - milestone_kind (str): "experience_type", "act_unlock", or "state_transition".
   - identifier (str): Transition name or token.
   - details (dict): Specific structured transition data.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from world.rules.event_log import EventLog
from world.rules.titles.awards import AutomaticTitleAward
from world.skills.registry import SKILL_REGISTRY, SkillCategory
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY


@dataclass(frozen=True)
class MilestoneSnapshot:
    """Snapshot of milestone-relevant sexual state taken before settlement."""

    experience_types: frozenset[str]
    unlocked_act_keys: frozenset[str]
    virgin: bool
    climax_count: int
    climax_phase: str


def _durable_pk(entity: Any) -> str:
    """Return the stable, persistent primary key for an entity."""
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


def capture_milestone_snapshot(entity: Any) -> MilestoneSnapshot | None:
    """Capture milestone-relevant sexual state for an entity before mutation."""
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return None
    try:
        current_phase = getattr(sexual.climax_phase, "level", None)
        if current_phase is None:
            current_phase = str(sexual.climax_phase)
        return MilestoneSnapshot(
            experience_types=frozenset(sexual.experience_types),
            unlocked_act_keys=frozenset(sexual.unlocked_act_keys()),
            virgin=bool(sexual.virgin),
            climax_count=int(sexual.climax_count),
            climax_phase=str(current_phase),
        )
    except (AttributeError, TypeError, ValueError):
        # A non-character or uninitialized entity without full sexual fields
        return None


def detect_new_milestones(entity: Any, before: MilestoneSnapshot | None) -> list[dict[str, Any]]:
    """Detect milestones newly crossed between before snapshot and current state.

    Existing lifetime counters or pre-existing state never create a milestone.
    """
    if before is None:
        return []
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return []

    milestones: list[dict[str, Any]] = []

    # 1. Experience types newly acquired
    current_exp = frozenset(sexual.experience_types)
    new_exp = current_exp - before.experience_types
    for exp in sorted(new_exp):
        milestones.append({
            "kind": "experience_type",
            "identifier": exp,
            "details": {"experience_type": exp},
        })

    # 2. Act unlock threshold actually crossed
    current_unlocked = frozenset(sexual.unlocked_act_keys())
    new_unlocked = current_unlocked - before.unlocked_act_keys
    for act_key in sorted(new_unlocked):
        milestones.append({
            "kind": "act_unlock",
            "identifier": act_key,
            "details": {"unlocked_act": act_key},
        })

    # 3. Virginity lost
    if before.virgin and not sexual.virgin:
        milestones.append({
            "kind": "state_transition",
            "identifier": "virginity_loss",
            "details": {"transition": "virginity_loss"},
        })

    # 4. First completed climax
    if before.climax_count == 0 and sexual.climax_count > 0:
        milestones.append({
            "kind": "state_transition",
            "identifier": "first_climax",
            "details": {"transition": "first_climax", "climax_count": int(sexual.climax_count)},
        })

    # 5. Climax peak onset (transition into 進行中)
    current_phase = getattr(sexual.climax_phase, "level", None)
    if current_phase is None:
        current_phase = str(sexual.climax_phase)
    if before.climax_phase != "進行中" and str(current_phase) == "進行中":
        milestones.append({
            "kind": "state_transition",
            "identifier": "climax_onset",
            "details": {"transition": "climax_onset", "phase": "進行中"},
        })

    # 6. Purity restored (e.g. restore_purity flips virgin False -> True)
    if (not before.virgin) and sexual.virgin:
        milestones.append({
            "kind": "state_transition",
            "identifier": "purity_restored",
            "details": {"transition": "purity_restored"},
        })

    return milestones


def build_action_source_id(
    request: Any,
    tick: int | None = None,
    narration_scope: str = "",
) -> str:
    """Format a stable, unique source identity for an action occurrence."""
    explicit_source = getattr(request, "source_id", None)
    if explicit_source:
        return str(explicit_source).strip()

    actor = request.actor
    actor_pk = _durable_pk(actor)
    req_context = getattr(request, "context", None)
    skill_key = getattr(request, "skill_key", "skill")
    battlefield = getattr(req_context, "battlefield", None)
    session_id = getattr(battlefield, "session_id", None)
    action_id = getattr(request, "action_id", None) or getattr(req_context, "action_id", None)

    if action_id:
        return f"action:{action_id}:{actor_pk}"

    if session_id:
        round_idx = None
        slot_idx = None
        if narration_scope:
            parts = narration_scope.replace(":", "|").split("|")
            numeric = [p for p in parts if p.isdigit()]
            if len(numeric) >= 2:
                round_idx, slot_idx = numeric[-2], numeric[-1]
            elif len(numeric) == 1:
                slot_idx = numeric[-1]
        if round_idx is None:
            round_idx = str(getattr(battlefield, "round_number", 1))
        if slot_idx is not None:
            return f"action:combat:{session_id}:r{round_idx}:s{slot_idx}:{actor_pk}:{skill_key}"
        return f"action:combat:{session_id}:r{round_idx}:{actor_pk}:{skill_key}"

    from world.rules.clock import get_world_clock
    current_tick = get_world_clock().tick if tick is None else int(tick)
    return f"action:cast:{actor_pk}:{skill_key}:{current_tick}"


def record_non_resolver_adult_milestones(
    entity: Any,
    before: MilestoneSnapshot | None,
    *,
    source_id: str,
    tick: int,
    location: str = "",
) -> list[Any]:
    """Record newly crossed adult milestones for non-resolver transition owners."""
    milestones = detect_new_milestones(entity, before)
    if not milestones:
        return []

    entity_pk = _durable_pk(entity)
    from world.narrative.events import record_narrative_event
    recorded = []
    for m in milestones:
        ms_source_id = f"{source_id}:milestone:{entity_pk}:{m['kind']}:{m['identifier']}"
        ms_content = {
            "action_source_id": source_id,
            "milestone_kind": m["kind"],
            "identifier": m["identifier"],
            "entity_id": entity_pk,
            "entity_name": str(getattr(entity, "key", "")),
            "details": m["details"],
            "tick": int(tick),
            "visibility": "private",
            "privacy": {
                "private_experience": True,
                "public_notoriety": False,
            },
        }
        event, _, _ = record_narrative_event(
            source_id=ms_source_id,
            event_type="adult_milestone",
            content=ms_content,
            participants=[entity_pk],
            location=str(location or ""),
            tick=int(tick),
            visibility="private",
            salience=1,
        )
        recorded.append(event)
    return recorded


def _check_external_observers(actor: Any, target_entities: Sequence[Any], room: Any) -> bool:
    """Check if third-party observers outside actor and targets are present."""
    if room is None:
        return False
    contents = getattr(room, "contents", None)
    if not contents:
        return False

    exempt_pks = {_durable_pk(actor)} | {_durable_pk(t) for t in target_entities}
    for obj in contents:
        if _durable_pk(obj) in exempt_pks:
            continue
        # If an unexempt character/NPC/monster is present, an audience exists
        has_living_surface = hasattr(obj, "traits") or hasattr(obj, "sexual") or getattr(obj, "has_account", False)
        if has_living_surface:
            return True
    return False


def record_action_settlement_evidence(
    request: Any,
    event_log: EventLog,
    title_awards: Sequence[AutomaticTitleAward],
    milestone_snapshots: Mapping[int, MilestoneSnapshot],
    *,
    narration_scope: str = "",
    tick: int | None = None,
    delivered_targets: Sequence[Any] = (),
    resisted_targets: Sequence[Any] = (),
) -> tuple[Any, list[Any]]:
    from world.rules.clock import get_world_clock
    """Record immutable narrative event and milestones for a settled action."""
    current_tick = get_world_clock().tick if tick is None else int(tick)
    from world.narrative.events import record_narrative_event
    source_id = build_action_source_id(request, tick=current_tick, narration_scope=narration_scope)

    skill = SKILL_REGISTRY.get(request.skill_key)
    is_adult = (
        (skill is not None and getattr(skill, "category", None) is SkillCategory.SEXUAL_ACT)
        or (skill is not None and getattr(skill, "key", "") in SEXUAL_ACT_REGISTRY)
    )

    actor = request.actor
    actor_pk = _durable_pk(actor)

    # Resolve actual recipients from exact delivered and resisted target entities
    # Untouched party members / bystanders are NEVER included.
    seen_target_pks: set[str] = set()
    actual_recipient_records: list[dict[str, Any]] = []
    actual_target_entities: list[Any] = []

    for target in list(delivered_targets) + list(resisted_targets):
        t_pk = _durable_pk(target)
        if t_pk not in seen_target_pks and t_pk != actor_pk:
            seen_target_pks.add(t_pk)
            actual_target_entities.append(target)
            actual_recipient_records.append({
                "id": t_pk,
                "name": str(getattr(target, "key", "")),
                "role": "recipient",
            })

    # If delivered_targets was empty but targets were in event_log (e.g. synthetic test call)
    if not actual_recipient_records and isinstance(getattr(request, "targets", None), list):
        for t in request.targets:
            t_pk = _durable_pk(t)
            t_key = str(getattr(t, "key", ""))
            # check if mentioned in event_log
            if any(str(getattr(e, "target", "")) in {t_key, t_pk} for e in event_log.entries):
                if t_pk not in seen_target_pks and t_pk != actor_pk:
                    seen_target_pks.add(t_pk)
                    actual_target_entities.append(t)
                    actual_recipient_records.append({
                        "id": t_pk,
                        "name": t_key,
                        "role": "recipient",
                    })

    # Participants list: actual actor and actual recipients only
    participants = [actor_pk] + [r["id"] for r in actual_recipient_records if r["id"] != actor_pk]

    # Location
    location = getattr(request.context, "room", None) or getattr(actor, "location", None)
    location_str = str(getattr(location, "pk", getattr(location, "id", str(location or ""))))

    # Visibility: third party observers check
    observed = _check_external_observers(actor, actual_target_entities, location)
    visibility = "public" if observed else "private"

    # Read structured event log entries
    effects_data: list[dict[str, Any]] = []
    resist_entries: list[dict[str, Any]] = []
    transition_entries: list[dict[str, Any]] = []
    counter_entries: list[dict[str, Any]] = []

    # Map target keys to durable IDs for outcome attribution
    key_to_pk = {str(getattr(actor, "key", "")): actor_pk}
    for t in actual_target_entities:
        key_to_pk[str(getattr(t, "key", ""))] = _durable_pk(t)

    for entry in event_log.entries:
        kind = getattr(entry, "kind", None)
        entry_actor_pk = key_to_pk.get(str(entry.actor), str(entry.actor))
        entry_target_pk = key_to_pk.get(str(entry.target), str(entry.target)) if entry.target else None
        data = dict(entry.data) if isinstance(getattr(entry, "data", None), Mapping) else {}

        if kind == "sexual_resist":
            resist_entries.append({
                "actor_id": entry_actor_pk,
                "target_id": entry_target_pk,
                "resisted": bool(data.get("resisted")),
                "auto_comply": bool(data.get("auto_comply")),
                "roll": data.get("roll"),
            })
        elif kind == "sexual_transition":
            transition_entries.append({
                "target_id": entry_target_pk or entry_actor_pk,
                "event": data.get("event"),
            })
        elif kind == "sexual_counter":
            counter_entries.append({
                "target_id": entry_target_pk or entry_actor_pk,
                "counter": data.get("counter"),
            })
        elif kind in {
            "damage", "heal", "self_heal", "buff_applied", "self_buff_applied",
            "buffs_cleansed", "pleasure_gain", "gauge_transfer",
        }:
            effects_data.append({
                "kind": kind,
                "actor_id": entry_actor_pk,
                "target_id": entry_target_pk,
                "data": data,
            })

    # Detect and record milestones for all involved participants
    milestone_events: list[Any] = []
    milestone_summaries: list[dict[str, Any]] = []
    all_participant_entities = [actor] + actual_target_entities

    for entity in all_participant_entities:
        e_pk = _durable_pk(entity)
        before_ms = milestone_snapshots.get(id(entity))
        if before_ms is not None:
            new_ms = detect_new_milestones(entity, before_ms)
            for m in new_ms:
                ms_source_id = f"{source_id}:milestone:{e_pk}:{m['kind']}:{m['identifier']}"
                ms_content = {
                    "action_source_id": source_id,
                    "milestone_kind": m["kind"],
                    "identifier": m["identifier"],
                    "entity_id": e_pk,
                    "entity_name": str(getattr(entity, "key", "")),
                    "details": m["details"],
                    "tick": current_tick,
                    "visibility": visibility,
                    "privacy": {
                        "private_experience": not observed,
                        "public_notoriety": False,
                    },
                }
                ms_event, _, _ = record_narrative_event(
                    source_id=ms_source_id,
                    event_type="adult_milestone",
                    content=ms_content,
                    participants=[e_pk],
                    location=location_str,
                    tick=current_tick,
                    visibility=visibility,
                    salience=1,
                )
                milestone_events.append(ms_event)
                milestone_summaries.append({
                    "source_id": ms_source_id,
                    "milestone_kind": m["kind"],
                    "identifier": m["identifier"],
                    "entity_id": e_pk,
                })

    # Build encounter context
    battlefield = getattr(request.context, "battlefield", None)
    encounter_context = None
    if battlefield is not None:
        encounter_context = {
            "session_id": str(getattr(battlefield, "session_id", "")),
            "round_number": int(getattr(battlefield, "round_number", 1)),
        }

    if is_adult:
        event_type = "adult_action"
        content: dict[str, Any] = {
            "action_source_id": source_id,
            "act_key": skill.key if skill else request.skill_key,
            "act_name": getattr(skill, "name", request.skill_key),
            "category": "sexual_act",
            "encounter_context": encounter_context,
            "actor": {
                "id": actor_pk,
                "name": str(getattr(actor, "key", "")),
                "role": "actor",
            },
            "recipients": actual_recipient_records,
            "outcomes": {
                "transitions": transition_entries,
                "counters": counter_entries,
                "resistance": resist_entries,
                "effects": effects_data,
            },
            "milestones": milestone_summaries,
            "visibility": visibility,
            "privacy": {
                "private_experience": not observed,
                "consent_inferred": False,       # NEVER infer consent from arousal/climax/auto-comply
                "willingness_inferred": False,   # NEVER infer willingness
                "relationship_inferred": False,  # NEVER infer relationship
                "public_notoriety": False,       # Private stays personal
            },
            "field_access": {
                actor_pk: ["actor", "act_key", "recipients", "resistance_verdict", "physical_effects"],
            },
        }
        for r in actual_recipient_records:
            content["field_access"][r["id"]] = ["target_own_outcome", "resistance_verdict", "effects_on_target"]
    else:
        event_type = "skill_use"
        content = {
            "action_source_id": source_id,
            "skill_key": skill.key if skill else request.skill_key,
            "skill_name": getattr(skill, "name", request.skill_key),
            "category": str(getattr(skill, "category", "skill")),
            "encounter_context": encounter_context,
            "actor": {
                "id": actor_pk,
                "name": str(getattr(actor, "key", "")),
                "role": "actor",
            },
            "recipients": actual_recipient_records,
            "effects": effects_data,
            "visibility": "public",
            "claim_limits": {
                "rescue_claimed": False,         # NEVER infer rescue or protection
                "protection_claimed": False,
                "exceptional_difficulty": False,
            },
        }

    action_event, _, _ = record_narrative_event(
        source_id=source_id,
        event_type=event_type,
        content=content,
        participants=participants,
        location=location_str,
        tick=current_tick,
        visibility=visibility,
        salience=1,
        award_results=title_awards,
    )
    return action_event, milestone_events
