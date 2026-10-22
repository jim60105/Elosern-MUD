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

4. Accepted settled-effect results (event evidence, written into
   `skill_use.effects` and `adult_action.outcomes.effects`):
   every admitted effect is a detached record of `kind`, `actor_id`,
   `target_id`, `target_name` and the committed `result` fields listed below.
   The kind names are the staged vocabulary production handlers emit
   (`world.rules.action.event_log`); a staged kind that is not listed here is
   not an effect of the settled action and SHALL NOT become deed evidence.
   Both accepted input forms — a staged `PendingEffect` description and a
   committed `EventEntry` — are normalized through the same table, so neither
   form can recognize a name the other does not.

   Accepted settled-effect results:
   - damage: amount, hit
   - heal: amount
   - self_heal: amount
   - gauge_transfer: gauge, direction, amount
   - pleasure_gain: amount
   - buff_applied: buff_key
   - self_buff_applied: buff_key
   - buffs_cleansed: count

   A `damage` result exists only for a hit: the canonical parser emits a roll
   entry alone for a miss, so a mistarget or a miss is never evidence of a
   committed effect. A `pleasure_gain` amount is the recipient's committed
   gauge change observed against the pre-settlement snapshot — the bounded
   gauge is the one staged amount production applies through a cap — never the
   requested magnitude.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from world.observability import log_info
from world.rules.event_log import EventLog
from world.rules.titles.awards import AutomaticTitleAward
from world.skills.registry import SKILL_REGISTRY, SkillCategory
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

#: Committed settled-effect kinds the deed evidence admits, with the committed
#: result fields each states, in declaration order. The names and result fields
#: mirror the staging sites in ``world.rules.action.event_log`` and its effect
#: handlers; the module docstring's "Accepted settled-effect results" list is
#: the reader-facing statement of this table.
_SETTLED_EFFECT_RESULTS: dict[str, tuple[tuple[str, type], ...]] = {
    "damage": (("amount", int), ("hit", bool)),
    "heal": (("amount", int),),
    "self_heal": (("amount", int),),
    "gauge_transfer": (("gauge", str), ("direction", str), ("amount", int)),
    "pleasure_gain": (("amount", int),),
    "buff_applied": (("buff_key", str),),
    "self_buff_applied": (("buff_key", str),),
    "buffs_cleansed": (("count", int),),
}

#: Effect kinds whose semantics bind them to the acting entity, so a committed
#: entry naming any target is still the actor's own result.
_SELF_BOUND_EFFECT_KINDS = frozenset({"self_heal", "self_buff_applied"})

#: Bounded gauge gain kinds whose staged amount is the requested magnitude, and
#: the pre-settlement snapshot field carrying the value they started from.
_BOUNDED_GAUGE_SNAPSHOT_FIELD = {"pleasure_gain": "pleasure_value"}


@dataclass(frozen=True)
class MilestoneSnapshot:
    """Snapshot of milestone-relevant sexual state taken before settlement."""

    experience_types: frozenset[str]
    unlocked_act_keys: frozenset[str]
    virgin: bool
    climax_count: int
    climax_phase: str
    pleasure_value: int | None


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
            pleasure_value=_stored_pleasure_value(entity),
        )
    except (AttributeError, TypeError, ValueError):  # observability: ignore R2: a non-character or uninitialized entity without full sexual fields has no milestone surface to capture; the entry's own writes are the report
        # A non-character or uninitialized entity without full sexual fields
        return None


def _stored_pleasure_value(entity: Any) -> int | None:
    """Read one entity's stored pleasure gauge, or ``None`` when unreadable.

    The bounded pleasure counter trait is read through its ``.value`` surface
    both before and after settlement, so an observed committed change compares
    like with like. An entity whose gauge cannot be read keeps every other
    captured field: an unreadable gauge only disables the observed committed
    amount, it never disables milestone capture.
    """
    try:
        return int(entity.sexual.pleasure.value)
    except (AttributeError, TypeError, ValueError):  # observability: ignore R2: an unreadable gauge only disables the observed committed amount; the record still commits with the staged magnitude
        return None


#: Post-settlement readers for the bounded gauge gains above, read through the
#: same surface their snapshot captured.
_BOUNDED_GAUGE_READERS = {"pleasure_gain": _stored_pleasure_value}


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


def _validated_settled_result(
    kind: str,
    candidate: Mapping[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    """State one committed effect's result in its admitted field vocabulary.

    Every admitted kind declares its result fields and their stated type in
    ``_SETTLED_EFFECT_RESULTS``. A payload that cannot state them (a missing
    field, or a value that is not a real integer, string or boolean) is
    malformed required evidence and fails its source transaction rather than
    becoming an empty or invented deed record.
    """
    result: dict[str, Any] = {}
    for field, stated_type in _SETTLED_EFFECT_RESULTS[kind]:
        if field not in candidate:
            raise ValueError(
                f"malformed {kind} committed result in {source}: missing {field}"
            )
        value = candidate[field]
        if stated_type is bool:
            if not isinstance(value, bool):
                raise ValueError(
                    f"malformed {kind} committed result in {source}: "
                    f"{field} is not a boolean"
                )
            result[field] = value
        elif stated_type is int:
            if isinstance(value, bool):
                raise ValueError(
                    f"malformed {kind} committed result in {source}: "
                    f"{field} is not an integer"
                )
            try:
                result[field] = int(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"malformed {kind} committed result in {source}: "
                    f"{field} is not an integer"
                ) from error
        else:
            if not isinstance(value, str):
                raise ValueError(
                    f"malformed {kind} committed result in {source}: "
                    f"{field} is not text"
                )
            result[field] = value
    return result


def _settled_result_from_values(
    kind: str,
    values: Sequence[str],
    *,
    source: str,
) -> dict[str, Any] | None:
    """Decode a staged ``PendingEffect`` description's trailing values.

    The decoding mirrors ``world.rules.action.event_log._entries_from_effect``,
    the canonical pending-description parser: the same arities, the same stated
    types and the same optional-field defaults. A damage miss stages no
    committed damage, so it yields ``None`` exactly as the canonical parser
    emits no damage entry for it.
    """
    if kind == "damage":
        if len(values) != 3:
            raise ValueError(f"malformed damage committed result in {source}")
        try:
            _roll, hit_flag, amount = (int(value) for value in values)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"malformed damage committed result in {source}"
            ) from error
        if not hit_flag:
            return None
        return _validated_settled_result(
            kind, {"amount": amount, "hit": True}, source=source
        )
    if kind in ("heal", "self_heal", "pleasure_gain"):
        if len(values) != 1:
            raise ValueError(f"malformed {kind} committed result in {source}")
        return _validated_settled_result(
            kind, {"amount": int(values[0])}, source=source
        )
    if kind == "gauge_transfer":
        candidate = {
            "gauge": values[0] if len(values) > 0 else "mp",
            "direction": values[1] if len(values) > 1 else "drain",
            "amount": int(values[2]) if len(values) > 2 else 0,
        }
        return _validated_settled_result(kind, candidate, source=source)
    if kind in ("buff_applied", "self_buff_applied"):
        if len(values) != 1:
            raise ValueError(f"malformed {kind} committed result in {source}")
        return _validated_settled_result(
            kind, {"buff_key": values[0]}, source=source
        )
    if kind == "buffs_cleansed":
        if len(values) != 1:
            raise ValueError(f"malformed {kind} committed result in {source}")
        return _validated_settled_result(
            kind, {"count": int(values[0])}, source=source
        )
    raise ValueError(f"unadmitted settled-effect kind {kind!r} in {source}")


def _settled_result_from_entry(
    kind: str,
    data: Mapping[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    """Decode one committed ``EventEntry`` payload into the same result shape.

    The canonical parser emits a damage entry only for a hit, so the entry
    itself establishes ``hit``; every other field is read from the entry's own
    committed data and validated against the same admitted vocabulary the
    staged form uses.
    """
    candidate = {
        field: data[field]
        for field, _ in _SETTLED_EFFECT_RESULTS[kind]
        if field in data
    }
    if kind == "damage":
        candidate.setdefault("hit", True)
    return _validated_settled_result(kind, candidate, source=source)


def _settled_effect_record(
    kind: str,
    actor_pk: str,
    target_id: str | None,
    target_name: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one detached committed-effect record for deed evidence.

    The result is narrowed to the kind's declared fields, so a caller cannot
    widen the evidence vocabulary by passing an extra key; the decode helpers
    have already validated the values.
    """
    return {
        "kind": kind,
        "actor_id": actor_pk,
        "target_id": target_id,
        "target_name": target_name,
        "result": {
            field: result[field] for field, _ in _SETTLED_EFFECT_RESULTS[kind]
        },
    }


def _committed_gauge_gain(
    entity: Any,
    kind: str,
    requested: int,
    milestone_snapshots: Mapping[int, MilestoneSnapshot],
) -> int:
    """Return the recipient's committed bounded-gauge change for one gain.

    The staged pleasure amount is the requested magnitude; the committed change
    is what the recipient's gauge actually holds after the action applied. It is
    observed once per recipient for the whole action (several staged gains sum
    into one committed change) and stated as the recipient's actual result. A
    recipient without a readable pre-settlement snapshot falls back to the
    requested amount, which is the only committed value left to state.
    """
    reader = _BOUNDED_GAUGE_READERS.get(kind)
    if reader is None:
        return requested
    snapshot = milestone_snapshots.get(id(entity))
    before = (
        getattr(snapshot, _BOUNDED_GAUGE_SNAPSHOT_FIELD[kind], None)
        if snapshot is not None
        else None
    )
    after = reader(entity)
    if before is None or after is None:
        return requested
    return max(0, after - before)


def _unique_key_index(entities: Sequence[Any]) -> dict[str, str]:
    """Map display keys to durable identities only where the key is unique.

    A display key is not an identifier, so a key two distinct candidates share
    resolves to nothing rather than to one of them.
    """
    seen: dict[str, list[str]] = {}
    for entity in entities:
        key = str(getattr(entity, "key", "") or "")
        if not key:
            continue
        pk = _durable_pk(entity)
        known = seen.setdefault(key, [])
        if pk not in known:
            known.append(pk)
    return {key: pks[0] for key, pks in seen.items() if len(pks) == 1}


def _entry_target(
    entry: Any,
    kind: str,
    key_index: Mapping[str, str],
    actor_pk: str,
    actor_key: str,
    *,
    source: str,
) -> tuple[str, str]:
    """Resolve one committed entry's target to ``(durable pk, display name)``.

    A kind whose semantics bind it to the acting entity resolves to the actor;
    every other entry resolves only through a unique candidate key. An
    ambiguous or unknown target fails its source transaction instead of being
    attributed to a guessed recipient.
    """
    raw = str(getattr(entry, "target", "") or "")
    if kind in _SELF_BOUND_EFFECT_KINDS or not raw:
        return actor_pk, actor_key
    resolved = key_index.get(raw)
    if resolved is None:
        raise ValueError(f"unresolvable settled evidence target in {source}")
    return resolved, raw


def _resistance_record(
    actor_pk: str,
    target_id: str,
    target_name: str,
    *,
    resisted: bool,
    auto_comply: bool,
    roll: int | None,
) -> dict[str, Any]:
    """Build one committed resistance verdict record."""
    return {
        "actor_id": actor_pk,
        "target_id": target_id,
        "target_name": target_name,
        "resisted": bool(resisted),
        "auto_comply": bool(auto_comply),
        "roll": None if roll is None else int(roll),
    }


def _transition_record(target_id: str, target_name: str, event: str) -> dict[str, Any]:
    """Build one committed own-state transition record."""
    return {"target_id": target_id, "target_name": target_name, "event": event}


def _counter_record(target_id: str, target_name: str, counter: str) -> dict[str, Any]:
    """Build one committed counter-change record."""
    return {"target_id": target_id, "target_name": target_name, "counter": counter}


def _required_text(value: Any, what: str, *, source: str) -> str:
    """Return one required committed text value or fail its source transaction."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"malformed {what} in {source}")
    return value


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
    pending_effects: Sequence[Any] = (),
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
    event_type = "adult_action" if is_adult else "skill_use"

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

    # Read settled results through the one admitted-result normalizer. Both
    # accepted input forms — the staged pending effects production passes and
    # the committed event log — converge here, so a kind one form recognizes is
    # never dropped by the other.
    effects_data: list[dict[str, Any]] = []
    resist_entries: list[dict[str, Any]] = []
    transition_entries: list[dict[str, Any]] = []
    counter_entries: list[dict[str, Any]] = []

    # Recipients of a bounded gauge gain, in first-appearance order. The staged
    # amount is the requested magnitude, so each recipient's committed change
    # is observed once for the whole action after every effect has applied.
    gauge_gains: dict[int, dict[str, Any]] = {}

    if pending_effects:
        for eff in pending_effects:
            desc = str(getattr(eff, "description", ""))
            eff_entity = getattr(eff, "entity", None)
            eff_pk = _durable_pk(eff_entity) if eff_entity is not None else actor_pk
            eff_name = str(getattr(eff_entity, "key", ""))
            parts = desc.split("|")
            kind = parts[0] if parts else ""
            values = parts[2:]
            source = f"{kind}:{eff_pk}"
            if kind == "sexual_resist":
                if len(values) != 3:
                    raise ValueError(f"malformed resistance evidence in {source}")
                # "none" is the canonical absent-roll sentinel staged by
                # ``action.gates._resist_pending_effect`` and parsed by
                # ``action.event_log``; auto-complied verdicts never roll, so
                # an absent roll is a normal result, never a parse failure.
                resist_entries.append(_resistance_record(
                    actor_pk,
                    eff_pk,
                    eff_name,
                    resisted=bool(int(values[0])),
                    auto_comply=bool(int(values[1])),
                    roll=None if values[2] == "none" else int(values[2]),
                ))
            elif kind == "sexual_transition":
                if len(values) != 1:
                    raise ValueError(f"malformed transition evidence in {source}")
                transition_entries.append(
                    _transition_record(eff_pk, eff_name, values[0])
                )
            elif kind == "sexual_counter":
                if len(values) != 1:
                    raise ValueError(f"malformed counter evidence in {source}")
                counter_entries.append(_counter_record(eff_pk, eff_name, values[0]))
            elif kind in _SETTLED_EFFECT_RESULTS:
                result = _settled_result_from_values(kind, values, source=source)
                if result is None:
                    # A damage miss commits no effect, exactly as the canonical
                    # parser emits no damage entry for it.
                    continue
                if kind in _BOUNDED_GAUGE_SNAPSHOT_FIELD:
                    identity = id(eff_entity)
                    gain = gauge_gains.get(identity)
                    if gain is None:
                        gauge_gains[identity] = {
                            "kind": kind,
                            "entity": eff_entity,
                            "target_id": eff_pk,
                            "target_name": eff_name,
                            "requested": int(result["amount"]),
                        }
                    else:
                        gain["requested"] += int(result["amount"])
                    continue
                effects_data.append(
                    _settled_effect_record(kind, actor_pk, eff_pk, eff_name, result)
                )
    else:
        actor_key = str(getattr(actor, "key", "") or "")
        candidates = [actor, *actual_target_entities]
        if isinstance(getattr(request, "targets", None), list):
            candidates.extend(request.targets)
        key_index = _unique_key_index(candidates)
        for entry in event_log.entries:
            kind = str(getattr(entry, "kind", "") or "")
            data = (
                dict(entry.data)
                if isinstance(getattr(entry, "data", None), Mapping)
                else {}
            )
            source = f"{kind}:{source_id}"
            if kind == "sexual_resist":
                target_id, target_name = _entry_target(
                    entry, kind, key_index, actor_pk, actor_key, source=source
                )
                resist_entries.append(_resistance_record(
                    actor_pk,
                    target_id,
                    target_name,
                    resisted=bool(data.get("resisted")),
                    auto_comply=bool(data.get("auto_comply")),
                    roll=data.get("roll"),
                ))
            elif kind == "sexual_transition":
                target_id, target_name = _entry_target(
                    entry, kind, key_index, actor_pk, actor_key, source=source
                )
                transition_entries.append(_transition_record(
                    target_id,
                    target_name,
                    _required_text(data.get("event"), "transition result", source=source),
                ))
            elif kind == "sexual_counter":
                target_id, target_name = _entry_target(
                    entry, kind, key_index, actor_pk, actor_key, source=source
                )
                counter_entries.append(_counter_record(
                    target_id,
                    target_name,
                    _required_text(data.get("counter"), "counter result", source=source),
                ))
            elif kind in _SETTLED_EFFECT_RESULTS:
                target_id, target_name = _entry_target(
                    entry, kind, key_index, actor_pk, actor_key, source=source
                )
                effects_data.append(_settled_effect_record(
                    kind,
                    actor_pk,
                    target_id,
                    target_name,
                    _settled_result_from_entry(kind, data, source=source),
                ))

    for gain in gauge_gains.values():
        kind = str(gain["kind"])
        committed = _committed_gauge_gain(
            gain["entity"], kind, int(gain["requested"]), milestone_snapshots
        )
        effects_data.append(_settled_effect_record(
            kind,
            actor_pk,
            str(gain["target_id"]),
            str(gain["target_name"]),
            {"amount": committed},
        ))
        if committed != int(gain["requested"]):
            # A bounded gauge change is the one committed result that can differ
            # from the staged amount; the repair is reported with identifiers
            # and numbers only, never the staged payload.
            log_info(
                "action_deed_evidence_normalized",
                context={
                    "source_id": source_id,
                    "event_type": event_type,
                    "kind": kind,
                    "target_id": str(gain["target_id"]),
                    "requested": int(gain["requested"]),
                    "committed": committed,
                },
            )

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
                    "visibility": "private",
                    "privacy": {
                        "private_experience": True,
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
                    visibility="private",
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
                actor_pk: [
                    "actor",
                    "act_key",
                    "recipients",
                    "resistance_verdict",
                    "physical_effects",
                    "own_state_transitions",
                    "own_counter_changes",
                    "actor_milestones",
                ],
            },
        }
        for r in actual_recipient_records:
            content["field_access"][r["id"]] = [
                "target_own_outcome",
                "resistance_verdict",
                "effects_on_target",
                "target_state_transitions",
                "target_counter_changes",
                "target_milestones",
            ]
    else:
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
