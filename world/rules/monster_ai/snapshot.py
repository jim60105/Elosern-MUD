"""No-create decision reads and the frozen snapshot they are projected from.

One monster decision takes exactly one :class:`DecisionReads`: the registry
lookup, the owned-skill metadata, the adjusted costs, the participant traits,
the effective-trait fold and the buff projections are each read once and
reused across every plan that decision validates. The reads never materialize
a lazy handler, never regenerate a gauge, never refresh a timestamp and never
write state: the persisted trait and buff attributes are read directly, and
the skill handler is constructed explicitly instead of through the entity's
lazy property.

The read set is deliberately single-decision scoped. It is never carried into
the next action, so an earlier action's resource, health or status change is
always visible to the next decision and no cross-action cache can hide it; a
later decision simply builds a new one.

Live entities enter only through the reads themselves. The snapshot they
produce holds no entity, no handler and no cache.
"""

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from world.rules.action.gates import _adjusted_costs
from world.rules.buffs import (
    BLOCKING_BUFF_KEYS,
    BUFF_DEFINITIONS,
    active_buff_entries_from_storage,
    active_buff_entries_keyed,
    active_buff_keys_from_storage,
    entity_active_buffs,
)
from world.rules.combat_modifiers import (
    build_no_create_condition_context,
    evaluate_combat_modifiers_no_create,
)
from world.rules.monster_ai.models import (
    BuffProjection,
    CapabilityState,
    DecisionScope,
    DecisionSnapshot,
    DivertLimit,
    OwnedSkillSnapshot,
    ParticipantSnapshot,
    PublicObservation,
    stable_identity,
)
from world.rules.traits import (
    GAUGE_KEYS,
    STATIC_KEYS,
    TRAIT_KEYS,
    stored_trait_records,
    trait_record_gauge_pair,
    trait_record_value,
)
from world.skills.handler import SkillHandler
from world.skills.registry import SKILL_REGISTRY, SkillDef


def _memo_key(entity: Any) -> Any:
    """Return the private memoization key of one participant.

    A persisted identity is preferred; an ephemeral double falls back to its
    object address, which is private to this one decision and never enters a
    snapshot, a fingerprint or a seed.
    """
    pk = getattr(entity, "pk", None)
    if isinstance(pk, int) and not isinstance(pk, bool):
        return pk
    return id(entity)


def _active_buff_keys(entity: Any) -> frozenset[str]:
    """Return the entity's active buff keys through the non-mutating read.

    A participant with a persisted attribute store is read from that store, so
    the buff handler is never attached; an ephemeral double without one falls
    back to its own handler. Both reads answer the same liveness question, so
    the blocked-by-buff fact never depends on which handler happens to be
    mounted.
    """
    if hasattr(entity, "attributes"):
        return frozenset(active_buff_keys_from_storage(entity))
    if hasattr(entity, "buffs"):
        return frozenset(entity_active_buffs(entity))
    return frozenset()


class DecisionReads:
    """One decision's stored reads, each taken once and reused across plans.

    Every method answers from the first read it took for that participant (or
    that skill, or that skill-and-scale pair) inside this decision. Nothing is
    cached across decisions, and no method writes, attaches a handler or
    advances a gauge.
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillDef | None] = {}
        self._owned: dict[Any, frozenset[str]] = {}
        self._modifiers: dict[Any, dict[str, Any]] = {}
        self._records: dict[Any, Mapping[str, Any]] = {}
        self._traits: dict[Any, Mapping[str, float]] = {}
        self._effective: dict[Any, Mapping[str, float]] = {}
        self._resources: dict[Any, Mapping[str, tuple[int, int]]] = {}
        self._buffs: dict[Any, frozenset[str]] = {}
        self._projections: dict[Any, tuple[BuffProjection, ...]] = {}
        self._capability: dict[Any, CapabilityState] = {}
        self._conditions: dict[Any, dict[str, Any]] = {}
        self._proficiency: dict[Any, Mapping[str, float]] = {}
        self._costs: dict[tuple[Any, str, float], dict[str, int]] = {}
        self._diverts: dict[Any, tuple[DivertLimit, ...]] = {}
        self._weapon_multipliers: dict[Any, float] = {}

    def skill(self, skill_key: str) -> SkillDef | None:
        """Return the registered skill definition behind one key."""
        if skill_key not in self._skills:
            self._skills[skill_key] = SKILL_REGISTRY.get(skill_key)
        return self._skills[skill_key]

    def owned_keys(self, entity: Any) -> frozenset[str]:
        """Return the entity's owned skill keys."""
        key = _memo_key(entity)
        if key not in self._owned:
            self._owned[key] = frozenset(SkillHandler(entity).owned_keys())
        return self._owned[key]

    def modifiers(self, entity: Any) -> dict[str, Any]:
        """Return the entity's merged combat-modifier bundle."""
        key = _memo_key(entity)
        if key not in self._modifiers:
            self._modifiers[key] = evaluate_combat_modifiers_no_create(entity)
        return self._modifiers[key]

    def weapon_multiplier(self, entity: Any) -> float:
        """Return the entity's declared weapon damage factor, memoized."""
        key = _memo_key(entity)
        if key not in self._weapon_multipliers:
            from world.rules.equipment_effects import equipment_weapon_multiplier

            self._weapon_multipliers[key] = equipment_weapon_multiplier(entity)
        return self._weapon_multipliers[key]


    def costs(self, entity: Any, skill: SkillDef, scale: float) -> dict[str, int]:
        """Return one skill's adjusted costs at ``scale`` for the entity."""
        key = (_memo_key(entity), skill.key, float(scale))
        if key not in self._costs:
            self._costs[key] = _adjusted_costs(
                entity, skill, scale, self.modifiers(entity)
            )
        return self._costs[key]

    def _trait_records(self, entity: Any) -> Mapping[str, Any]:
        """Return DETACHED copies of the entity's persisted trait records.

        The persisted mapping is read once and then copied record by record, so
        a later write to entity storage can never change an answer this read
        set already gave. The old read set answers the old values even though
        the snapshot scalars were already projected from them.
        """
        key = _memo_key(entity)
        if key not in self._records:
            self._records[key] = MappingProxyType(
                {
                    name: MappingProxyType(dict(record))
                    for name, record in stored_trait_records(entity).items()
                    if isinstance(record, Mapping)
                }
            )
        return self._records[key]

    def condition_context(self, entity: Any) -> dict[str, Any]:
        """Return the entity's stored condition context, read once.

        The shared no-create condition builder (buff cache, stored sexual
        levels, effective exposure, worn items) behind the cast-condition
        mini-language, so a decision evaluates every plan's conditions against
        one build per participant.
        """
        key = _memo_key(entity)
        if key not in self._conditions:
            self._conditions[key] = build_no_create_condition_context(entity)
        return self._conditions[key]

    def proficiency(self, entity: Any) -> Mapping[str, float]:
        """Return a detached copy of the entity's stored practice XP."""
        key = _memo_key(entity)
        if key not in self._proficiency:
            stored = getattr(getattr(entity, "db", None), "skill_proficiency", None)
            self._proficiency[key] = MappingProxyType(
                dict(stored) if isinstance(stored, Mapping) else {}
            )
        return self._proficiency[key]

    def gauge_maximum(self, entity: Any, gauge_key: str) -> int | None:
        """Return one stored gauge maximum, or ``None`` when unreadable."""
        pair = trait_record_gauge_pair(
            self._trait_records(entity).get(gauge_key)
        )
        return None if pair is None else pair[1]

    def trait_value(self, entity: Any, trait_key: str) -> float:
        """Return one stored trait value, or ``0.0`` when it is absent."""
        value = trait_record_value(self._trait_records(entity).get(trait_key))
        return 0.0 if value is None else value

    def hp(self, entity: Any) -> float:
        """Return one participant's stored hp for the shared aliveness gate."""
        return self.trait_value(entity, "hp")

    def trait_map(self, entity: Any) -> Mapping[str, float]:
        """Return the TRUE literal stored values of every combat trait."""
        key = _memo_key(entity)
        if key not in self._traits:
            records = self._trait_records(entity)
            self._traits[key] = MappingProxyType(
                {
                    trait_key: value
                    for trait_key in TRAIT_KEYS
                    if (value := trait_record_value(records.get(trait_key)))
                    is not None
                }
            )
        return self._traits[key]

    def effective_traits(self, entity: Any) -> Mapping[str, float]:
        """Return the static combat traits after the owned-passive fold."""
        key = _memo_key(entity)
        if key not in self._effective:
            folded = SkillHandler(entity).stored_effective_values(STATIC_KEYS)
            self._effective[key] = MappingProxyType(
                {trait_key: float(value) for trait_key, value in folded.items()}
            )
        return self._effective[key]

    def resources(self, entity: Any) -> Mapping[str, tuple[int, int]]:
        """Return the stored ``(current, maximum)`` pair of every gauge."""
        key = _memo_key(entity)
        if key not in self._resources:
            records = self._trait_records(entity)
            pairs: dict[str, tuple[int, int]] = {}
            for gauge_key in GAUGE_KEYS:
                pair = trait_record_gauge_pair(records.get(gauge_key))
                if pair is not None:
                    pairs[gauge_key] = pair
            self._resources[key] = MappingProxyType(pairs)
        return self._resources[key]

    def blocked_by_buff(self, entity: Any) -> bool:
        """Return whether a blocking buff forbids the entity's action."""
        return bool(self.buff_keys(entity) & BLOCKING_BUFF_KEYS)

    def buff_keys(self, entity: Any) -> frozenset[str]:
        """Return the entity's active buff definition keys."""
        key = _memo_key(entity)
        if key not in self._buffs:
            self._buffs[key] = _active_buff_keys(entity)
        return self._buffs[key]

    def buff_projections(self, entity: Any) -> tuple[BuffProjection, ...]:
        """Return the entity's active buffs projected from persisted state."""
        key = _memo_key(entity)
        if key not in self._projections:
            self._projections[key] = _project_buffs(entity)
        return self._projections[key]

    def capability(self, entity: Any) -> CapabilityState:
        """Return the entity's action-capability projection."""
        key = _memo_key(entity)
        if key not in self._capability:
            modifiers = self.modifiers(entity)
            self._capability[key] = CapabilityState(
                blocked_by_buff=self.blocked_by_buff(entity),
                actions_per_turn=int(modifiers.get("actions_per_turn", 1)),
            )
        return self._capability[key]

    def divert_limits(self, entity: Any) -> tuple[DivertLimit, ...]:
        """Return the entity's active damage-diversion budgets, read once.

        Projected from the persisted buff cache through the shared no-create
        liveness reader and the shipped buff definitions, so an estimate can
        subtract a known shield without mounting the buff handler or running
        settlement. The order is settlement's own: definition key first, then
        the buff instance key, because that order is which budget absorbs a
        strike's residual first once a cap starts binding.
        """
        key = _memo_key(entity)
        if key not in self._diverts:
            self._diverts[key] = _divert_limits(entity)
        return self._diverts[key]


def _divert_limits(entity: Any) -> tuple[DivertLimit, ...]:
    """Project one entity's active damage-diversion budgets from storage.

    The shipped buff definition owns the authored fraction, cap and paid
    gauge (all three validated at load time); the persisted cache entry owns
    how much of that cap the instance has already spent. Nothing here mounts a
    handler, so one decision can subtract a known shield from an estimate
    without running the damage handler.
    """
    if not hasattr(entity, "attributes"):
        return ()
    limits: list[DivertLimit] = []
    for instance_key, entry in active_buff_entries_keyed(entity):
        definition_key = entry.get("definition_key")
        if not isinstance(definition_key, str):
            continue
        definition = BUFF_DEFINITIONS.get(definition_key)
        if definition is None:
            continue
        spec = definition.modifiers.get("divert")
        if not isinstance(spec, Mapping):
            continue
        spent = entry.get("divert_consumed")
        if isinstance(spent, bool) or not isinstance(spent, (int, float)):
            spent = 0
        limits.append(
            DivertLimit(
                instance_key=instance_key,
                definition_key=definition_key,
                gauge=str(spec["target"]),
                fraction=float(spec["fraction"]),
                remaining_cap=max(0, int(spec["cap"]) - max(0, int(spent))),
            )
        )
    limits.sort(key=lambda limit: (limit.definition_key, limit.instance_key))
    return tuple(limits)


def _project_buffs(entity: Any) -> tuple[BuffProjection, ...]:
    """Project one entity's persisted active buff entries in stable key order."""
    if not hasattr(entity, "attributes"):
        return ()
    projections: list[BuffProjection] = []
    for entry in active_buff_entries_from_storage(entity):
        definition_key = entry.get("definition_key")
        if not isinstance(definition_key, str):
            continue
        definition = BUFF_DEFINITIONS.get(definition_key)
        remaining = entry.get("remaining_seconds")
        projections.append(
            BuffProjection(
                key=definition_key,
                stacks=entry["stacks"],
                remaining_seconds=(
                    remaining if isinstance(remaining, int) else None
                ),
                marker=None if definition is None else definition.marker,
            )
        )
    return tuple(sorted(projections, key=lambda buff: buff.key))


def _participant_snapshot(
    actor: Any,
    context: Any,
    entity: Any,
    reads: DecisionReads,
) -> ParticipantSnapshot:
    """Project one live participant into its immutable snapshot."""
    return ParticipantSnapshot(
        identity=stable_identity(entity),
        relation=context.relation_to(actor, entity),
        present=bool(context.is_present(actor, entity)),
        in_range=bool(context.is_in_range(actor, entity)),
        alive=reads.hp(entity) > 0,
        traits=reads.trait_map(entity),
        effective_traits=reads.effective_traits(entity),
        resources=reads.resources(entity),
        capability=reads.capability(entity),
        buffs=reads.buff_projections(entity),
    )


def _owned_skills(actor: Any, reads: DecisionReads) -> tuple[OwnedSkillSnapshot, ...]:
    """Project the actor's owned skill metadata in stable key order."""
    snapshots: list[OwnedSkillSnapshot] = []
    for skill_key in sorted(reads.owned_keys(actor)):
        definition = reads.skill(skill_key)
        if definition is None:
            continue
        snapshots.append(
            OwnedSkillSnapshot(
                key=definition.key,
                kind=definition.kind,
                target_spec=definition.target_spec,
                faction_constraint=definition.faction_constraint,
            )
        )
    return tuple(snapshots)


def build_decision_snapshot(
    actor: Any,
    context: Any,
    *,
    scope: DecisionScope,
    participants: Sequence[Any] = (),
    observations: Sequence[PublicObservation] = (),
    context_mode: str = "normal",
    reads: DecisionReads | None = None,
) -> DecisionSnapshot:
    """Build one decision's frozen input from no-create reads.

    The actor and every participant it does not already name are projected
    once through ``reads``. The identity facts, the context mode and the
    settled public observations the caller supplies are recorded verbatim;
    nothing else about the world is read, so a queued player request, an
    unresolved teammate choice and a disguised stat cannot reach the snapshot.
    """
    reader = DecisionReads() if reads is None else reads
    pool = [actor]
    seen = {_memo_key(actor)}
    for participant in participants:
        key = _memo_key(participant)
        if key in seen:
            continue
        seen.add(key)
        pool.append(participant)
    snapshots = tuple(
        _participant_snapshot(actor, context, entity, reader) for entity in pool
    )
    return DecisionSnapshot(
        scope=scope,
        actor=snapshots[0],
        participants=snapshots[1:],
        owned_skills=_owned_skills(actor, reader),
        species_key=getattr(actor, "species_key", None),
        variant_key=getattr(actor, "variant_key", None),
        threat_tier=getattr(actor, "threat_tier", None),
        context_mode=context_mode,
        observations=tuple(observations),
    )
