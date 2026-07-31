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
    """A live, two-team combat roster."""

    teams: dict[str, frozenset[str]]
    roster: dict[str, Any]
    fled: set[str] = field(default_factory=set)

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


class BattlefieldActionContext:
    """Targeting context backed by one active battlefield."""

    def __init__(
        self,
        battlefield: Battlefield,
        event_context: dict[str, Any] | None = None,
    ):
        self.battlefield = battlefield
        self.event_context = {} if event_context is None else dict(event_context)
        supplied = self.event_context.get("battlefield", battlefield)
        if supplied is not battlefield:
            raise ValueError("event_context battlefield must match context battlefield")
        self.event_context["battlefield"] = battlefield

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


def _noop() -> None:
    """Commit-time no-op for a staged miss."""


def _handle_damage(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage d100 hit and damage results; commit only the computed hp delta."""
    _, school = _parse_damage_effect(effect_id)
    attack_key = "atk_phys" if school == "physical" else "magic_level"
    pending: list[PendingEffect] = []
    for target in targets:
        raw_roll = roll_d100()
        hit, margin = _to_hit(actor, target, raw_roll)
        amount = 0
        if hit:
            multiplier = _roll_multiplier(raw_roll, margin)
            attack = actor.skills.effective_value(attack_key)
            defense = target.skills.effective_value("defense")
            amount = max(
                round(attack * multiplier) - defense,
                int(COMBAT_YAML["damage"]["floor"]),
            )
        pending.append(
            PendingEffect(
                entity=target,
                description=(
                    f"damage|{target.key}|{raw_roll}|{int(hit)}|{amount}"
                ),
                surfaces=frozenset(),
                apply=(
                    lambda target=target, amount=amount: _apply_hp_delta(
                        target, -amount
                    )
                )
                if hit
                else _noop,
            )
        )
    return pending


register_effect_handler(
    "damage",
    _handle_damage,
    surfaces=frozenset({"traits"}),
)


def roll_initiative(battlefield: Battlefield) -> list[str]:
    """Return living, active roster keys in descending initiative order."""
    weight = COMBAT_YAML["initiative"]["agility_weight"]
    scores = {
        key: entity.skills.effective_value("agility") * weight + roll_d100()
        for key, entity in battlefield.roster.items()
        if key not in battlefield.fled and _stored_hp(entity) > 0
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
        if key in battlefield.fled or _stored_hp(entity) <= 0:
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
