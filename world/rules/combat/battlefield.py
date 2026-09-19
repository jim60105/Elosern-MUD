"""Battlefield roster, read-only power helpers, and terminal predicates.

This module owns the shipped ``combat.yaml`` rulebook and the roster surface
every other combat module reads: the ``Battlefield``/
``BattlefieldActionContext`` pair, the bounded-encounter ``BattleResult``, the
stored-hp and effective-stat readers, and the initiative/terminal predicates.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.dice import roll_d100
from world.rules.event_log import EventLog
from world.rules.items import ItemUseRequest
from world.rules.targeting import Relation


COMBAT_YAML = yaml.safe_load(
    (Path(__file__).parent.parent / "rulebook" / "combat.yaml").read_text(
        encoding="utf-8"
    )
)

_MAX_ACTIONS_PER_TURN: int = 3


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

    def is_in_range(self, actor: Any, target: Any) -> bool:
        """Treat every active roster member as engaged until positions exist."""
        return target.key not in self.battlefield.fled


@dataclass(frozen=True)
class BattleResult:
    """Structured result from a bounded deterministic encounter."""

    event_logs: tuple[EventLog, ...]
    rounds_elapsed: int
    total_seconds: int
    completed: bool


RoundRequest = ActionRequest | ItemUseRequest

ActionProvider = Callable[[Any, Battlefield], RoundRequest | None]


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


def effective_power(entity: Any) -> float:
    """Return the four-stat effective sum scaled by maximum hp."""
    stat_sum = sum(
        entity.skills.effective_value(key)
        for key in ("atk_phys", "agility", "defense", "magic_power")
    )
    return float(stat_sum) * _max_hp(entity)


def _adjusted_attack(entity: Any, attack_key: str) -> float:
    """Return effective attack plus the matching flat bundle bonus.

    The ``atk_phys`` bonus enters only physical attacks, the ``magic_power``
    bonus (mage robes, staves, magic swords) only the magic school, each
    matching the stat's role in the damage formula; neither school receives
    the other stat's adjustment.
    """
    attack = float(entity.skills.effective_value(attack_key))
    if attack_key not in {"atk_phys", "magic_power"}:
        return attack
    return attack + evaluate_combat_modifiers(entity).get(attack_key, 0)


def _adjusted_defense(entity: Any) -> float:
    """Return effective defense plus the flat ``defense`` bundle bonus."""
    return float(entity.skills.effective_value("defense")) + evaluate_combat_modifiers(
        entity
    ).get("defense", 0)


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
