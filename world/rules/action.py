"""Atomic, deterministic skill-action resolution."""

from copy import deepcopy
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Callable, Literal

from django.db import transaction

from typeclasses.monsters import Monster
from world.rules.buffs import (
    _add_buff,
    blocks_action,
    entity_active_buffs,
    grant_conferred_growth_rate,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.progression import grant_combat_kill_xp, grant_skill_practice_xp
from world.rules.skill_effects import (
    apply_disguise_effect,
    record_conferred_grant,
)
from world.rules.targeting import (
    ActionContext,
    expand_target_shorthand,
    resolve_targets,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec


class RejectReason(StrEnum):
    """Stable rejection identifiers for every action-pipeline failure."""

    UNKNOWN_SKILL = "unknown_skill"
    SKILL_NOT_ACTIVE = "skill_not_active"
    SKILL_NOT_USABLE_OUT_OF_COMBAT = "skill_not_usable_out_of_combat"
    INSUFFICIENT_RESOURCE = "insufficient_resource"
    TARGET_SPEC_MISMATCH = "target_spec_mismatch"
    TARGET_NOT_PRESENT = "target_not_present"
    TARGET_DEAD = "target_dead"
    TARGET_OUT_OF_RANGE = "target_out_of_range"
    TARGET_FACTION_FORBIDDEN = "target_faction_forbidden"
    NO_VALID_TARGETS_IN_AREA = "no_valid_targets_in_area"
    ACTION_FORBIDDEN = "action_forbidden"
    UNKNOWN_EFFECT_ID = "unknown_effect_id"
    EFFECT_RESOLUTION_FAILED = "effect_resolution_failed"
    RESOURCE_DEDUCTION_FAILED = "resource_deduction_failed"
    EVENT_LOG_CONSTRUCTION_FAILED = "event_log_construction_failed"
    TIME_COST_LOOKUP_FAILED = "time_cost_lookup_failed"
    UNSNAPSHOTTED_EFFECT_SURFACE = "unsnapshotted_effect_surface"
    COMMIT_FAILED = "commit_failed"


class RejectedAction(Exception):
    """A pre-commit action rejection."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class CommitFailed(Exception):
    """A commit rejection after state has been restored."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ActionRequest:
    """One caller-neutral request to invoke a skill."""

    actor: Any
    skill_key: str
    targets: list[Any] | Literal["all-enemies", "all-allies", "all"]
    context: ActionContext


@dataclass(frozen=True)
class ActionResult:
    """Success or rejection returned without leaking pipeline exceptions."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None
    time_cost_seconds: int | None
    reason: RejectReason | None
    detail: str | None

    @classmethod
    def success(cls, event_log: EventLog, time_cost: int) -> "ActionResult":
        return cls("success", event_log, time_cost, None, None)

    @classmethod
    def rejected(
        cls,
        reason: RejectReason,
        detail: str = "",
    ) -> "ActionResult":
        return cls("rejected", None, None, reason, detail)


@dataclass(frozen=True)
class PendingEffect:
    """A state mutation staged for the single commit point."""

    entity: Any
    description: str
    surfaces: frozenset[str]
    apply: Callable[[], None]


class UnsnapshottedSurfaceError(Exception):
    """A handler declared state that the commit mechanism cannot restore."""


EffectHandler = Callable[
    [Any, list[Any], str, dict[str, Any]],
    list[PendingEffect],
]
SNAPSHOTTED_SURFACES = frozenset(
    {"traits", "sexual", "buffs", "skill_grants", "progression", "battlefield"}
)
_EFFECT_HANDLERS: dict[str, EffectHandler] = {}
_EFFECT_HANDLER_SURFACES: dict[str, frozenset[str]] = {}
DEFAULT_CAST_SECONDS = 6
SKILL_TIME_OVERRIDES: dict[str, int] = {}


def register_effect_handler(
    prefix: str,
    handler: EffectHandler,
    surfaces: frozenset[str],
) -> None:
    """Register an effect prefix only when all mutations are restorable."""
    unsupported = surfaces - SNAPSHOTTED_SURFACES
    if unsupported:
        raise UnsnapshottedSurfaceError(
            f"{prefix!r} declares unsupported surfaces {sorted(unsupported)}"
        )
    _EFFECT_HANDLERS[prefix] = handler
    _EFFECT_HANDLER_SURFACES[prefix] = surfaces


def _entity_key(entity: Any) -> str:
    return str(entity.key)


def _event_context(request: ActionRequest) -> dict[str, Any]:
    return getattr(request.context, "event_context", {})


def _step1_ownership(request: ActionRequest) -> SkillDef:
    skill = SKILL_REGISTRY.get(request.skill_key)
    if skill is None or skill.key not in request.actor.skills.owned_keys():
        raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)
    if skill.kind is not SkillKind.ACTIVE:
        raise RejectedAction(RejectReason.SKILL_NOT_ACTIVE, request.skill_key)
    # The ONE sanctioned combat-context read in this entire module — see design.md D-3.
    if not skill.usable_out_of_combat and request.context.battlefield is None:
        raise RejectedAction(
            RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT,
            request.skill_key,
        )
    return skill


def _step2_resource_check(actor: Any, skill: SkillDef) -> None:
    for resource_key, amount in skill.cost.items():
        if _stored_trait_value(getattr(actor.traits, resource_key)) < amount:
            raise RejectedAction(
                RejectReason.INSUFFICIENT_RESOURCE,
                resource_key,
            )


def _step3_targeting(
    request: ActionRequest,
    skill: SkillDef,
) -> list[Any]:
    candidates = (
        expand_target_shorthand(
            request.actor,
            request.context,
            request.targets,
        )
        if isinstance(request.targets, str)
        else list(request.targets)
    )
    if skill.target_spec is TargetSpec.SELF and not candidates:
        candidates = [request.actor]
    return resolve_targets(request, skill, candidates)


def _step4_capability(actor: Any) -> None:
    if actor.attributes.has("buffs") and blocks_action(actor):
        raise RejectedAction(RejectReason.ACTION_FORBIDDEN, _entity_key(actor))


def _require_context(context: dict[str, Any], *keys: str) -> tuple[Any, ...]:
    try:
        return tuple(context[key] for key in keys)
    except KeyError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"missing event_context key {error.args[0]!r}",
        ) from error


def _handle_confer_skill_partial(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
) -> list[PendingEffect]:
    skill_key, scale, trait_keys = _require_context(
        context,
        "confer_skill_key",
        "confer_scale",
        "confer_trait_keys",
    )
    target = targets[0]
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"skill_granted|{_entity_key(target)}|{skill_key}|{scale}",
            frozenset(),
            lambda: record_conferred_grant(
                target,
                source_key,
                skill_key,
                tuple(trait_keys),
                float(scale),
            ),
        )
    ]


def _handle_set_disguise(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
) -> list[PendingEffect]:
    overrides = context.get("disguise", context.get("overrides"))
    if not isinstance(overrides, dict):
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "set_disguise requires event_context.disguise",
        )
    target = targets[0]
    return [
        PendingEffect(
            target,
            f"disguise_set|{_entity_key(target)}",
            frozenset(),
            lambda: apply_disguise_effect(target, overrides),
        )
    ]


def _handle_buff_apply(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
) -> list[PendingEffect]:
    try:
        key = effect_id.split(":", 1)[1]
    except IndexError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            effect_id,
        ) from error
    kwargs = dict(context.get("buff_kwargs", {}))
    return [
        PendingEffect(
            target,
            f"buff_applied|{_entity_key(target)}|{key}",
            frozenset(),
            lambda target=target: _add_buff(target, key, **kwargs),
        )
        for target in targets
    ]


def _handle_confer_growth_rate(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
) -> list[PendingEffect]:
    (scale,) = _require_context(context, "confer_scale")
    target = targets[0]
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"buff_applied|{_entity_key(target)}|conferred_growth_rate",
            frozenset(),
            lambda: grant_conferred_growth_rate(
                target,
                source_key,
                float(scale),
            ),
        )
    ]


def _handle_sexual_event(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
) -> list[PendingEffect]:
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    event_name = effect_id.partition(":")[2]
    if not event_name:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual_event requires an event name",
        )
    sexual_context = dict(context.get("sexual", {}))
    return [
        PendingEffect(
            target,
            f"sexual_transition|{_entity_key(target)}|{event_name}",
            frozenset(),
            lambda target=target: apply_event(
                target,
                event_name,
                **sexual_context,
            ),
        )
        for target in targets
    ]


register_effect_handler(
    "confer_skill_partial",
    _handle_confer_skill_partial,
    frozenset({"skill_grants"}),
)
register_effect_handler(
    "set_disguise",
    _handle_set_disguise,
    frozenset({"traits"}),
)
register_effect_handler(
    "buff_apply",
    _handle_buff_apply,
    frozenset({"buffs"}),
)
register_effect_handler(
    "confer_growth_rate",
    _handle_confer_growth_rate,
    frozenset({"buffs"}),
)
register_effect_handler(
    "sexual_event",
    _handle_sexual_event,
    frozenset({"sexual", "traits"}),
)


def _effect_prefix(effect_id: str) -> str:
    return effect_id.partition(":")[0]


def _step5_effect_resolution(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
) -> list[PendingEffect]:
    pending: list[PendingEffect] = []
    context = _event_context(request)
    for effect_id in skill.effects:
        prefix = _effect_prefix(effect_id)
        handler = _EFFECT_HANDLERS.get(prefix)
        if handler is None:
            raise RejectedAction(RejectReason.UNKNOWN_EFFECT_ID, effect_id)
        try:
            effects = handler(request.actor, targets, effect_id, context)
            surfaces = _EFFECT_HANDLER_SURFACES[prefix]
            for effect in effects:
                if not isinstance(effect, PendingEffect):
                    raise TypeError(
                        "effect handler returned a non-PendingEffect value"
                    )
                pending.append(replace(effect, surfaces=surfaces))
        except RejectedAction:
            raise
        except Exception as error:
            raise RejectedAction(
                RejectReason.EFFECT_RESOLUTION_FAILED,
                f"{effect_id}: {error}",
            ) from error
    return pending


def _deduct_resource(trait: Any, amount: int) -> None:
    if hasattr(trait, "current"):
        trait.current = trait.current - amount
    else:
        trait.value = trait.value - amount


def _step6_resource_deduction(
    actor: Any,
    skill: SkillDef,
) -> list[PendingEffect]:
    pending = []
    for resource_key, amount in skill.cost.items():
        trait = getattr(actor.traits, resource_key)
        if _stored_trait_value(trait) < amount:
            raise RejectedAction(
                RejectReason.RESOURCE_DEDUCTION_FAILED,
                resource_key,
            )
        pending.append(
            PendingEffect(
                actor,
                f"resource_spend|{_entity_key(actor)}|{resource_key}|{amount}",
                frozenset({"traits"}),
                lambda trait=trait, amount=amount: _deduct_resource(trait, amount),
            )
        )
    return pending


def _step6_skill_practice(actor: Any, skill: SkillDef) -> PendingEffect:
    """Stage one practice award inside the action's transactional commit."""
    return PendingEffect(
        actor,
        f"skill_practice|{_entity_key(actor)}|{skill.key}",
        frozenset({"progression"}),
        lambda: grant_skill_practice_xp(actor, skill.key),
    )


def _step6_combat_kill_xp(
    request: ActionRequest,
    targets: list[Any],
) -> list[PendingEffect]:
    """Stage one post-damage kill award per initially living tiered monster."""
    if request.context.battlefield is None:
        return []
    pending: list[PendingEffect] = []
    seen: set[int] = set()
    for target in targets:
        if id(target) in seen:
            continue
        seen.add(id(target))
        if not isinstance(target, Monster):
            continue
        tier_key = target.threat_tier
        if tier_key not in MONSTER_TIER_REGISTRY or _stored_trait_value(target.traits.hp) <= 0:
            continue
        pending.append(
            PendingEffect(
                request.actor,
                f"combat_kill_xp|{_entity_key(target)}|{tier_key}",
                frozenset({"progression"}),
                lambda target=target, tier_key=tier_key: (
                    grant_combat_kill_xp(request.actor, tier_key)
                    if _stored_trait_value(target.traits.hp) <= 0
                    else None
                ),
            )
        )
    return pending


_ENTRY_TEMPLATES = {
    "resource_spend": "{actor} 消耗了資源。",
    "skill_granted": "{actor} 對 {target} 施展了「統御術」的部分效果。",
    "disguise_set": "{actor} 改變了 {target} 的偽裝狀態。",
    "buff_applied": "{actor} 對 {target} 施加了狀態效果。",
    "sexual_transition": "{target} 的狀態發生了變化。",
    "trait_delta": "{target} 的能力值發生了變化。",
    "roll": "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
    "damage": "{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
    "disengage_attempt": "{actor} 嘗試脫離戰鬥。",
    "skill_practice": "{actor} 累積了技能熟練度。",
    "combat_kill_xp": "",
}


def _entries_from_effect(
    actor_key: str,
    effect: PendingEffect,
) -> tuple[EventEntry, ...]:
    parts = effect.description.split("|")
    if len(parts) < 2 or parts[0] not in _ENTRY_TEMPLATES:
        raise ValueError(f"malformed pending-effect description {effect.description!r}")
    kind, target, *values = parts
    if kind == "resource_spend":
        data = {
            "resource_key": values[0],
            "amount": int(values[1]),
        }
    elif kind == "skill_granted":
        data = {
            "skill_key": values[0],
            "scale": float(values[1]),
        }
    elif kind == "buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "sexual_transition":
        data = {"event": values[0]}
    elif kind == "damage":
        if len(values) != 3:
            raise ValueError(
                f"malformed damage pending effect {effect.description!r}"
            )
        raw_roll, hit_flag, amount = map(int, values)
        roll_entry = EventEntry(
            kind="roll",
            actor=actor_key,
            target=target,
            data={"raw_roll": raw_roll, "hit": bool(hit_flag)},
            text_template=_ENTRY_TEMPLATES["roll"],
        )
        if not hit_flag:
            return (roll_entry,)
        return (
            roll_entry,
            EventEntry(
                kind="damage",
                actor=actor_key,
                target=target,
                data={"amount": amount},
                text_template=_ENTRY_TEMPLATES["damage"],
            ),
        )
    elif kind == "disengage_attempt":
        if len(values) != 4:
            raise ValueError(
                f"malformed disengage pending effect {effect.description!r}"
            )
        success_flag, raw_roll, actor_agility, pursuer_agility = values
        data = {
            "success": bool(int(success_flag)),
            "roll": None if raw_roll == "none" else int(raw_roll),
            "actor_agility": float(actor_agility),
            "pursuer_agility": (
                None
                if pursuer_agility == "none"
                else float(pursuer_agility)
            ),
        }
    elif kind == "combat_kill_xp":
        return ()
    else:
        data = {}
    entry = EventEntry(
        kind=kind,
        actor=actor_key,
        target=target,
        data=data,
        text_template=_ENTRY_TEMPLATES[kind],
    )
    if kind != "resource_spend":
        return (entry,)
    return (
        entry,
        EventEntry(
            kind="trait_delta",
            actor=actor_key,
            target=target,
            data={
                "trait_key": data["resource_key"],
                "delta": -data["amount"],
            },
            text_template=_ENTRY_TEMPLATES["trait_delta"],
        ),
    )


def _step7_build_event_log(
    request: ActionRequest,
    skill: SkillDef,
    pending: list[PendingEffect],
) -> EventLog:
    try:
        entries = tuple(
            entry
            for effect in pending
            for entry in _entries_from_effect(
                _entity_key(request.actor),
                effect,
            )
        )
    except Exception as error:
        raise RejectedAction(
            RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
            str(error),
        ) from error
    return EventLog(
        actor=_entity_key(request.actor),
        skill_key=skill.key,
        targets=_logged_targets(pending),
        entries=entries,
        time_cost_seconds=0,
    )


def _logged_targets(pending: list[PendingEffect]) -> tuple[str, ...]:
    targets: list[str] = []
    for effect in pending:
        if effect.description.startswith(("resource_spend|", "combat_kill_xp|")):
            continue
        key = effect.description.split("|", 2)[1]
        if key not in targets:
            targets.append(key)
    return tuple(targets)


def _step8_time_cost(request: ActionRequest, skill: SkillDef) -> int:
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise RejectedAction(
            RejectReason.TIME_COST_LOOKUP_FAILED,
            f"{skill.key}: {seconds!r}",
        )
    return seconds


def _stored_trait_value(trait: Any) -> float:
    """Read deterministic stored state without advancing a wall-clock gauge."""
    data = trait._data
    if trait.trait_type == "gauge":
        return data.get(
            "current",
            (data["base"] + data["mod"]) * data["mult"],
        )
    return data.get("value", (data.get("base", 0) + data.get("mod", 0)) * data.get("mult", 1))


def _attribute_snapshot(
    entity: Any,
    key: str,
    category: str | None = None,
) -> tuple[bool, Any]:
    exists = entity.attributes.has(key, category=category)
    value = (
        deepcopy(entity.attributes.get(key, category=category))
        if exists
        else None
    )
    return exists, value


def _snapshot_entity_state(entity: Any) -> dict[str, Any]:
    return {
        "traits": _attribute_snapshot(entity, "traits", "traits"),
        "disguised_stats": _attribute_snapshot(entity, "disguised_stats"),
        "sexual_traits": _attribute_snapshot(
            entity,
            "sexual_traits",
            "traits",
        ),
        "virgin": _attribute_snapshot(entity, "virgin", "sexual_state"),
        "experience_types": _attribute_snapshot(
            entity,
            "experience_types",
            "sexual_state",
        ),
        "buffs": _attribute_snapshot(entity, "buffs"),
        "skill_grants": _attribute_snapshot(entity, "skill_grants"),
        "magic_xp": _attribute_snapshot(entity, "magic_xp"),
        "skill_proficiency": _attribute_snapshot(entity, "skill_proficiency"),
    }


def _restore_attribute(
    entity: Any,
    key: str,
    snapshot: tuple[bool, Any],
    category: str | None = None,
) -> None:
    existed, value = snapshot
    if existed:
        entity.attributes.add(key, deepcopy(value), category=category)
    else:
        entity.attributes.remove(key, category=category)


def _restore_entity_state(entity: Any, snapshot: dict[str, Any]) -> None:
    _restore_attribute(entity, "traits", snapshot["traits"], "traits")
    _restore_attribute(entity, "disguised_stats", snapshot["disguised_stats"])
    _restore_attribute(
        entity,
        "sexual_traits",
        snapshot["sexual_traits"],
        "traits",
    )
    _restore_attribute(entity, "virgin", snapshot["virgin"], "sexual_state")
    _restore_attribute(
        entity,
        "experience_types",
        snapshot["experience_types"],
        "sexual_state",
    )
    _restore_attribute(entity, "buffs", snapshot["buffs"])
    _restore_attribute(entity, "skill_grants", snapshot["skill_grants"])
    _restore_attribute(entity, "magic_xp", snapshot["magic_xp"])
    _restore_attribute(entity, "skill_proficiency", snapshot["skill_proficiency"])
    entity.traits.trait_data = entity.attributes.get(
        "traits",
        default={},
        category="traits",
    )
    entity.traits._cache.clear()
    entity.__dict__.pop("sexual", None)


def _is_battlefield_like(obj: Any) -> bool:
    """Return whether an object exposes the encounter state this resolver owns."""
    return hasattr(obj, "fled") and hasattr(obj, "roster")


def _snapshot_touched(obj: Any) -> dict[str, Any]:
    """Snapshot either a battlefield mutation surface or entity state."""
    if _is_battlefield_like(obj):
        return {"fled": frozenset(obj.fled)}
    return _snapshot_entity_state(obj)


def _restore_touched(obj: Any, snapshot: dict[str, Any]) -> None:
    """Restore an object through the same shape-based snapshot dispatch."""
    if _is_battlefield_like(obj):
        obj.fled = set(snapshot["fled"])
        return
    _restore_entity_state(obj, snapshot)


def _commit(pending: list[PendingEffect]) -> None:
    for effect in pending:
        unsupported = effect.surfaces - SNAPSHOTTED_SURFACES
        if unsupported:
            raise CommitFailed(
                RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                f"{effect.description}: {sorted(unsupported)}",
            )
    touched: list[Any] = []
    touched_ids: set[int] = set()
    for effect in pending:
        identity = id(effect.entity)
        if identity not in touched_ids:
            touched.append(effect.entity)
            touched_ids.add(identity)
    snapshots = {
        id(entity): _snapshot_touched(entity)
        for entity in touched
    }
    try:
        with transaction.atomic():
            for effect in pending:
                effect.apply()
    except Exception as error:
        for entity in touched:
            _restore_touched(entity, snapshots[id(entity)])
        raise CommitFailed(RejectReason.COMMIT_FAILED, str(error)) from error


class ActionResolver:
    """The sole state-writing gateway for skill invocation."""

    @staticmethod
    def resolve(request: ActionRequest) -> ActionResult:
        try:
            skill = _step1_ownership(request)
            _step2_resource_check(request.actor, skill)
            targets = _step3_targeting(request, skill)
            _step4_capability(request.actor)
            pending = _step5_effect_resolution(request, skill, targets)
            pending += _step6_resource_deduction(request.actor, skill)
            pending.append(_step6_skill_practice(request.actor, skill))
            pending += _step6_combat_kill_xp(request, targets)
            event_log = _step7_build_event_log(request, skill, pending)
            time_cost = _step8_time_cost(request, skill)
            event_log = replace(event_log, time_cost_seconds=time_cost)
        except RejectedAction as rejection:
            return ActionResult.rejected(rejection.reason, rejection.detail)
        try:
            _commit(pending)
        except CommitFailed as failure:
            return ActionResult.rejected(failure.reason, failure.detail)
        return ActionResult.success(event_log, time_cost)
