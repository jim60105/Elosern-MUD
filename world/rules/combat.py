"""Deterministic d100 combat built on the shared action resolver."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    _stored_trait_value,
    register_effect_handler,
)
from world.rules.buffs import tick_buffs
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.dice import roll_d100
from world.rules.event_log import EventEntry, EventLog
from world.rules.progression import can_cast_skill
from world.rules.sexual_state import decay_tick
from world.rules.targeting import Relation
from world.skills.registry import SKILL_REGISTRY, SkillKind


COMBAT_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "combat.yaml").read_text(
        encoding="utf-8"
    )
)
_PERCENT_RE = re.compile(r"([+-]\d+)%")


@dataclass
class Battlefield:
    """A live, two-team combat roster.

    ``fled`` and ``knocked_out`` are the battlefield's persistent in-battle
    state sets (party-combat D-2): ``knocked_out`` holds the roster keys
    knocked out nonlethally at damage-commit time, so initiative, action
    provision, target selection, overwhelm classification, and terminal checks
    share one predicate instead of re-reading raw HP.
    """

    teams: dict[str, frozenset[str]]
    roster: dict[str, Any]
    fled: set[str] = field(default_factory=set)
    knocked_out: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if len(self.teams) != 2:
            raise ValueError("a battlefield requires exactly two teams")
        members = [key for team in self.teams.values() for key in team]
        if len(members) != len(set(members)):
            raise ValueError("a combatant cannot belong to multiple teams")
        if set(members) != set(self.roster):
            raise ValueError("team membership must exactly match the roster")
        for key, entity in self.roster.items():
            if key != str(entity.key):
                raise ValueError(
                    f"roster key {key!r} does not match entity key {entity.key!r}"
                )

    def team_of(self, key: str) -> str | None:
        """Return the team containing an entity key."""
        return next(
            (team for team, members in self.teams.items() if key in members),
            None,
        )

    def is_knocked_out(self, key: str) -> bool:
        """Whether one roster key is marked knocked out on the battlefield."""
        return key in self.knocked_out


class BattlefieldActionContext:
    """Targeting context backed by one active battlefield.

    ``nonlethal`` carries a deterministic knockout policy for examination
    combat: a lethal HP crossing floors the target at 1 HP and emits
    ``target_knocked_out`` instead of ``target_defeated`` before any
    event-effect planner observes the result (guild-economy D-7).
    """

    def __init__(
        self,
        battlefield: Battlefield,
        event_context: dict[str, Any] | None = None,
        nonlethal: bool = False,
    ):
        self.battlefield = battlefield
        self.nonlethal = nonlethal
        self.event_context = {} if event_context is None else dict(event_context)
        supplied = self.event_context.get("battlefield", battlefield)
        if supplied is not battlefield:
            raise ValueError("event_context battlefield must match context battlefield")
        self.event_context["battlefield"] = battlefield
        if nonlethal:
            self.event_context["nonlethal"] = True

    def is_present(self, actor: Any, target: Any) -> bool:
        return target.key in self.battlefield.roster

    def relation_to(self, actor: Any, target: Any) -> Relation:
        if actor is target:
            return Relation.SELF
        actor_team = self.battlefield.team_of(actor.key)
        target_team = self.battlefield.team_of(target.key)
        return (
            Relation.ALLY
            if actor_team is not None and actor_team == target_team
            else Relation.ENEMY
        )

    def is_in_range(self, actor: Any, target: Any, skill: Any) -> bool:
        """Treat every active roster member as engaged until positions exist."""
        return target.key not in self.battlefield.fled


@dataclass(frozen=True)
class BattleResult:
    """Structured result from a bounded deterministic encounter."""

    event_logs: tuple[EventLog, ...]
    rounds_elapsed: int
    total_seconds: int
    completed: bool


ActionProvider = Callable[[Any, Battlefield], ActionRequest | None]


def _stored_hp(entity: Any) -> float:
    return float(_stored_trait_value(entity.traits.hp))


def _max_hp(entity: Any) -> float:
    trait = entity.traits.hp
    maximum = getattr(trait, "max", None)
    if maximum is None:
        maximum = getattr(trait, "max_value", None)
    if maximum is None:
        maximum = _stored_trait_value(trait)
    return max(float(maximum), 0.0)


def _apply_percent_mod(base: float, pct: str | None) -> float:
    """Apply a signed percentage string from the modifier rulebook."""
    if pct is None:
        return base
    match = _PERCENT_RE.fullmatch(pct)
    if match is None:
        raise ValueError(f"invalid percentage modifier {pct!r}")
    return base * (1 + int(match.group(1)) / 100)


def _roll_multiplier(raw_roll: int, margin: float) -> float:
    damage = COMBAT_YAML["damage"]
    if raw_roll == 100:
        return float(damage["crit_multiplier"])
    if margin >= damage["solid_hit_margin"]:
        return float(damage["solid_hit_multiplier"])
    return float(damage["base_multiplier"])


def _to_hit(
    attacker: Any,
    defender: Any,
    raw_roll: int,
) -> tuple[bool, float]:
    attacker_mods = evaluate_combat_modifiers(attacker)
    defender_mods = evaluate_combat_modifiers(defender)
    attacker_agility = _apply_percent_mod(
        attacker.skills.effective_value("agility"),
        attacker_mods.get("agility"),
    )
    defender_agility = _apply_percent_mod(
        defender.skills.effective_value("agility"),
        defender_mods.get("agility"),
    )
    attack_score = (
        raw_roll + attacker_agility + attacker_mods.get("accuracy", 0)
    )
    threshold = (
        COMBAT_YAML["to_hit"]["defender_constant"] + defender_agility
    )
    margin = attack_score - threshold
    return margin >= 0, margin


def effective_power(entity: Any) -> float:
    """Return the four-stat effective sum scaled by maximum hp."""
    stat_sum = sum(
        entity.skills.effective_value(key)
        for key in ("atk_phys", "agility", "defense", "magic_level")
    )
    return float(stat_sum) * _max_hp(entity)


def _adjusted_attack(entity: Any, attack_key: str) -> float:
    """Return effective attack plus the flat ``atk_phys`` bundle bonus.

    The bonus enters only physical attacks (``attack_key == "atk_phys"``),
    matching the stat's role in the damage formula: magic-school damage reads
    ``magic_level`` and never receives the physical-attack adjustment.
    """
    attack = entity.skills.effective_value(attack_key)
    if attack_key != "atk_phys":
        return float(attack)
    return float(attack) + evaluate_combat_modifiers(entity).get("atk_phys", 0)


def _adjusted_defense(entity: Any) -> float:
    """Return effective defense plus the flat ``defense`` bundle bonus."""
    return float(entity.skills.effective_value("defense")) + evaluate_combat_modifiers(
        entity
    ).get("defense", 0)


def _parse_damage_effect(effect_id: str) -> tuple[str, str]:
    parts = effect_id.split(":")
    if len(parts) != 3 or parts[0] != "damage":
        raise ValueError(
            "damage effect must be damage:<element>:<school>"
        )
    _, element, school = parts
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown damage element {element!r}")
    if school not in {"physical", "magic"}:
        raise ValueError(f"unknown damage school {school!r}")
    return element, school


def _apply_hp_delta(entity: Any, delta: int) -> None:
    trait = entity.traits.hp
    if hasattr(trait, "current"):
        trait.current = _stored_trait_value(trait) + delta
    else:
        trait.value = _stored_trait_value(trait) + delta


def _apply_hp_delta_nonlethal(entity: Any, delta: int) -> None:
    """Apply damage with a knockout floor: a lethal crossing stops at 1 HP.

    The projection applies the ordinary delta, then any positive-to-zero-or-
    below crossing is clamped to 1 instead of reaching zero, so the target is
    knocked out rather than defeated (guild-economy D-7).
    """
    trait = entity.traits.hp
    current = _stored_trait_value(trait)
    projected = current + delta
    if current > 0 and projected <= 0:
        projected = 1
    if hasattr(trait, "current"):
        trait.current = projected
    else:
        trait.value = projected


def _noop() -> None:
    """Commit-time no-op for a staged miss."""


def _handle_damage(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage d100 hit and damage results; commit only the computed hp delta.

    The nonlethal policy is per-damaged-target (party-combat D-3): the
    session-wide ``nonlethal`` flag (examinations) protects every target, while
    ``nonlethal_keys`` protects only the named entities (allied companions in a
    hostile session). A protected crossing floors HP at 1; a crossing protected
    by the per-entity key set also stages a battlefield ``knocked_out`` mark
    inside the same commit, so the in-round initiative, targeting, overwhelm,
    and terminal consumers observe the knockout through the shared predicate.
    """
    _, school = _parse_damage_effect(effect_id)
    attack_key = "atk_phys" if school == "physical" else "magic_level"
    session_nonlethal = bool(event_context.get("nonlethal", False))
    nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
    battlefield = event_context.get("battlefield")
    pending: list[PendingEffect] = []
    for target in targets:
        raw_roll = roll_d100()
        hit, margin = _to_hit(actor, target, raw_roll)
        amount = 0
        if hit:
            multiplier = _roll_multiplier(raw_roll, margin)
            attack = _adjusted_attack(actor, attack_key)
            defense = _adjusted_defense(target)
            amount = max(
                round(attack * multiplier) - defense,
                int(COMBAT_YAML["damage"]["floor"]),
            )
            amount = int(amount)
        key = str(target.key)
        protected = session_nonlethal or key in nonlethal_keys
        marked: list[str] = []

        def apply(
            target=target,
            amount=amount,
            hit=hit,
            key=key,
            protected=protected,
            marked=marked,
        ) -> None:
            if not hit:
                _noop()
                return
            if not protected:
                _apply_hp_delta(target, -amount)
                return
            before = _stored_trait_value(target.traits.hp)
            _apply_hp_delta_nonlethal(target, -amount)
            if before > 0 and before - amount <= 0 and key in nonlethal_keys:
                marked.append(key)

        pending.append(
            PendingEffect(
                entity=target,
                description=(
                    f"damage|{key}|{raw_roll}|{int(hit)}|{amount}"
                ),
                surfaces=frozenset(),
                apply=apply,
            )
        )
        if key in nonlethal_keys and battlefield is not None:
            # One battlefield-shaped effect per protected target: the commit's
            # duck-typed snapshot/restore dispatch captures ``fled`` and
            # ``knocked_out`` by shape, so a later commit failure rolls the
            # mark back with the HP floor (battlefield-commit-surface).
            pending.append(
                PendingEffect(
                    entity=battlefield,
                    description=f"knocked_out_mark|{key}",
                    surfaces=frozenset(),
                    apply=lambda marked=marked: (
                        battlefield.knocked_out.update(marked)
                    ),
                )
            )
    return pending


register_effect_handler(
    "damage",
    _handle_damage,
    surfaces=frozenset({"traits"}),
    requires_event_context=frozenset(),
)


def _heal_magnitude(actor: Any) -> int:
    """Return the caster-stat-derived HP restoration amount for one heal.

    Substitutes a healing coefficient for damage's roll-derived multiplier and
    drops the defense-mitigation term entirely (healing is not mitigated), so
    the magnitude shares damage's ``round(effective value x multiplier)``
    shape without inheriting its to-hit or defense assumptions (design.md
    magnitude decision).
    """
    multiplier = float(COMBAT_YAML["heal"]["multiplier"])
    return max(
        round(actor.skills.effective_value("magic_level") * multiplier),
        int(COMBAT_YAML["heal"]["floor"]),
    )


def _parse_heal_effect(effect_id: str) -> str:
    parts = effect_id.split(":")
    if len(parts) != 2 or parts[0] != "heal" or parts[1] not in {"single", "area"}:
        raise ValueError("heal effect must be heal:single or heal:area")
    return parts[1]


def _restored_amount(entity: Any, amount: int) -> int:
    """Return how much of a heal actually applies to one entity right now.

    An entity that is not alive restores nothing (a heal never revives), and
    the restoration is capped by the remaining gap to the entity's maximum so
    the staged event log reflects the real HP increase.
    """
    current = _stored_trait_value(entity.traits.hp)
    if current <= 0:
        return 0
    return min(amount, max(0, _max_hp(entity) - current))


def _apply_heal(entity: Any, amount: int) -> None:
    """Restore HP clamped to the entity's maximum; never revives or decreases.

    The commit-time alive guard keeps the no-revival invariant even when an
    earlier effect in the same action reduced the entity below 1 HP after
    staging: such an entity stays knocked out.
    """
    trait = entity.traits.hp
    current = _stored_trait_value(trait)
    if current <= 0:
        return
    clamped = min(_max_hp(entity), current + amount)
    if hasattr(trait, "current"):
        trait.current = clamped
    else:
        trait.value = clamped


def _handle_heal(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage one HP-restoring pending effect per already-validated target.

    The magnitude is computed at staging time from caster stats, mirroring
    ``damage``; the per-target restoration is clamped by that target's current
    HP gap so the staged event log reports the real increase, and the
    commit-time closure re-checks aliveness and the cap.
    """
    del event_context
    _parse_heal_effect(effect_id)
    amount = _heal_magnitude(actor)
    pending: list[PendingEffect] = []
    for target in targets:
        key = str(target.key)
        restored = _restored_amount(target, amount)
        pending.append(
            PendingEffect(
                entity=target,
                description=f"heal|{key}|{restored}",
                surfaces=frozenset(),
                apply=lambda target=target, restored=restored: _apply_heal(
                    target, restored
                ),
            )
        )
    return pending


def _handle_self_heal(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage one HP-restoring pending effect bound to the caster.

    Mirrors ``self_buff_apply``'s actor-binding pattern: a target-list-driven
    heal cannot express "the caster heals themself while the same cast also
    damages an enemy", so this effect binds the actor instead of ``targets``.
    """
    del targets, event_context
    if effect_id != "self_heal":
        raise ValueError("self_heal effect takes no argument")
    amount = _heal_magnitude(actor)
    restored = _restored_amount(actor, amount)
    return [
        PendingEffect(
            entity=actor,
            description=f"self_heal|{str(actor.key)}|{restored}",
            surfaces=frozenset(),
            apply=lambda: _apply_heal(actor, restored),
        )
    ]


register_effect_handler(
    "heal",
    _handle_heal,
    surfaces=frozenset({"traits"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "self_heal",
    _handle_self_heal,
    surfaces=frozenset({"traits"}),
    requires_event_context=frozenset(),
)


def roll_initiative(battlefield: Battlefield) -> list[str]:
    """Return living, active roster keys in descending initiative order."""
    weight = COMBAT_YAML["initiative"]["agility_weight"]
    scores = {
        key: entity.skills.effective_value("agility") * weight + roll_d100()
        for key, entity in battlefield.roster.items()
        if key not in battlefield.fled
        and not battlefield.is_knocked_out(key)
        and _stored_hp(entity) > 0
    }
    return sorted(scores, key=lambda key: (-scores[key], key))


def default_attack_policy(
    entity: Any,
    battlefield: Battlefield,
) -> ActionRequest | None:
    """Placeholder for Monster.behaviour_tree: attack the weakest enemy."""
    enemy_team = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != battlefield.team_of(entity.key)
        ),
        frozenset(),
    )
    candidates = [
        battlefield.roster[key]
        for key in enemy_team
        if key not in battlefield.fled
        and key in battlefield.roster
        and not battlefield.is_knocked_out(key)
        and _stored_hp(battlefield.roster[key]) > 0
    ]
    if not candidates:
        return None
    skill_key = next(
        (
            key
            for key in entity.skills.owned_keys()
            if key in SKILL_REGISTRY
            and SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
            and any(
                effect.startswith("damage:")
                for effect in SKILL_REGISTRY[key].effects
            )
            and all(
                _stored_trait_value(getattr(entity.traits, resource)) >= amount
                for resource, amount in SKILL_REGISTRY[key].cost.items()
            )
            and can_cast_skill(entity, SKILL_REGISTRY[key])
        ),
        None,
    )
    if skill_key is None:
        return None
    target = min(
        candidates,
        key=lambda candidate: (_stored_hp(candidate), candidate.key),
    )
    return ActionRequest(
        actor=entity,
        skill_key=skill_key,
        targets=[target],
        context=BattlefieldActionContext(battlefield),
    )


def _action_skipped_event_log(entity: Any) -> EventLog:
    key = str(entity.key)
    entry = EventEntry(
        kind="action_skipped",
        actor=key,
        target=None,
        data={},
        text_template="{actor} 無法行動。",
    )
    return EventLog(key, "", (), (entry,), 0)


def _end_of_round_upkeep(battlefield: Battlefield) -> None:
    seconds = int(COMBAT_YAML["round"]["seconds"])
    for key, entity in battlefield.roster.items():
        if key in battlefield.fled or _stored_hp(entity) <= 0:
            continue
        tick_buffs(entity, seconds)
        decay_tick(entity, seconds)


def run_round(
    battlefield: Battlefield,
    action_provider: ActionProvider,
) -> list[EventLog]:
    """Resolve one action per capable combatant, then perform upkeep."""
    logs: list[EventLog] = []
    for key in roll_initiative(battlefield):
        entity = battlefield.roster[key]
        if (
            key in battlefield.fled
            or battlefield.is_knocked_out(key)
            or _stored_hp(entity) <= 0
        ):
            continue
        modifiers = evaluate_combat_modifiers(entity)
        if modifiers.get("actions_per_turn", 1) == 0:
            logs.append(_action_skipped_event_log(entity))
            continue
        request = action_provider(entity, battlefield)
        if request is None:
            continue
        result = ActionResolver.resolve(request)
        if result.outcome == "success" and result.event_log is not None:
            logs.append(result.event_log)
    _end_of_round_upkeep(battlefield)
    return logs


def is_battle_over(battlefield: Battlefield) -> bool:
    """Return whether either team has no living, non-fled combatants."""
    return any(
        not any(
            key not in battlefield.fled
            and key in battlefield.roster
            and not battlefield.is_knocked_out(key)
            and _stored_hp(battlefield.roster[key]) > 0
            for key in members
        )
        for members in battlefield.teams.values()
    )


def run_battle(
    battlefield: Battlefield,
    action_provider: ActionProvider = default_attack_policy,
    max_rounds: int = 100,
) -> BattleResult:
    """Run a bounded encounter and report, but do not settle, elapsed time."""
    if max_rounds < 0:
        raise ValueError("max_rounds must be non-negative")
    logs: list[EventLog] = []
    rounds = 0
    while rounds < max_rounds and not is_battle_over(battlefield):
        logs.extend(run_round(battlefield, action_provider))
        rounds += 1
    return BattleResult(
        event_logs=tuple(logs),
        rounds_elapsed=rounds,
        total_seconds=rounds * int(COMBAT_YAML["round"]["seconds"]),
        completed=is_battle_over(battlefield),
    )


# Combat is the production composition root for combat-owned effect handlers.
from world.rules import disengage as _disengage  # noqa: E402,F401
