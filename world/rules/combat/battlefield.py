"""Battlefield roster, read-only power helpers, and terminal predicates.

This module owns the shipped ``combat.yaml`` rulebook and the roster surface
every other combat module reads: the ``Battlefield``/
``BattlefieldActionContext`` pair, the bounded-encounter ``BattleResult``, the
stored-hp and effective-stat readers, and the initiative/terminal predicates.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat_modifiers import (
    attack_with_bundle,
    defense_with_bundle,
    evaluate_combat_modifiers,
)
from world.rules.dice import roll_d100
from world.rules.event_log import EventLog
from world.rules.items import ItemUseRequest
from world.rules.targeting import Relation


class CombatRulebookError(ValueError):
    """The combat rulebook is malformed, missing required entries, or out of bounds."""


def validate_combat_rulebook(data: Any) -> dict[str, Any]:
    """Validate one loaded combat rulebook mapping against required schema contracts.

    Finite positive ``damage.mitigation_k`` is strictly required: boolean,
    non-numeric, non-finite (inf/nan), zero, and negative values raise
    ``CombatRulebookError``.

    The round-start tactical constants are strictly required too: finite
    ``tactics.defend_reduction`` within ``[0, 1)`` and finite non-negative
    ``tactics.dodge_threshold_bonus`` are the only admitted values.
    """
    if not isinstance(data, dict):
        raise CombatRulebookError("combat rulebook must be a mapping")
    damage = data.get("damage")
    if not isinstance(damage, dict):
        raise CombatRulebookError("combat rulebook must declare a 'damage' mapping")
    if "mitigation_k" not in damage:
        raise CombatRulebookError("damage section must declare 'mitigation_k'")
    k = damage["mitigation_k"]
    if isinstance(k, bool) or not isinstance(k, (int, float)):
        raise CombatRulebookError(
            f"damage.mitigation_k must be a finite positive number, got {k!r}"
        )
    if not isfinite(float(k)) or float(k) <= 0:
        raise CombatRulebookError(
            f"damage.mitigation_k must be a finite positive number, got {k!r}"
        )
    tactics = data.get("tactics")
    if not isinstance(tactics, dict):
        raise CombatRulebookError("combat rulebook must declare a 'tactics' mapping")
    reduction = tactics.get("defend_reduction")
    if (
        isinstance(reduction, bool)
        or not isinstance(reduction, (int, float))
        or not isfinite(float(reduction))
        or not 0.0 <= float(reduction) < 1.0
    ):
        raise CombatRulebookError(
            "tactics.defend_reduction must be a finite number in [0, 1), "
            f"got {reduction!r}"
        )
    bonus = tactics.get("dodge_threshold_bonus")
    if (
        isinstance(bonus, bool)
        or not isinstance(bonus, (int, float))
        or not isfinite(float(bonus))
        or float(bonus) < 0.0
    ):
        raise CombatRulebookError(
            "tactics.dodge_threshold_bonus must be a finite non-negative number, "
            f"got {bonus!r}"
        )
    return data


def load_combat_rulebook(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the combat rulebook from path or canonical disk location."""
    target_path = path or (Path(__file__).parent.parent / "rulebook" / "combat.yaml")
    raw = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    return validate_combat_rulebook(raw)


COMBAT_YAML = load_combat_rulebook()

_MAX_ACTIONS_PER_TURN: int = 3


@dataclass(frozen=True)
class RoundTactical:
    """One round's activated round-start tactical declarations by roster key.

    ``declarations`` maps an allied roster key to its selected tactical verb
    (``"defend"`` or ``"dodge"``). The object is round-transient: it lives only
    in the round execution context (``Battlefield.tactical``), is never a
    durable buff, and expires when the round ends. It is the one channel
    settlement's damage staging and the monster-AI estimator both read, so
    ``is_defending``/``is_dodging`` cannot disagree between them.

    ``taunt_winners`` maps one taunted enemy's roster key to the roster key of
    the taunter that won that enemy for this round (the first taunter of that
    enemy in the round's own initiative sequence). One winner is stored per
    enemy, so a losing declaration can never take over; a winner that later
    becomes unable to act is revalidated live by
    :meth:`Battlefield.taunt_winner` rather than promoted from a runner-up.
    """

    declarations: dict[str, str]
    taunt_winners: dict[str, str] = field(default_factory=dict)

    def tactic_for(self, key: str) -> str | None:
        """Return the activated tactical verb for one roster key, or ``None``."""
        return self.declarations.get(key)

    def is_defending(self, key: str) -> bool:
        """Return whether one roster key declared Defend for the active round."""
        return self.declarations.get(key) == "defend"

    def is_dodging(self, key: str) -> bool:
        """Return whether one roster key declared Dodge for the active round."""
        return self.declarations.get(key) == "dodge"

    def taunter_for(self, enemy_key: str) -> str | None:
        """Return the winning taunter's roster key for one enemy, or ``None``."""
        return self.taunt_winners.get(enemy_key)


@dataclass
class Battlefield:
    """A live, two-team combat roster.

    ``fled`` and ``knocked_out`` are the battlefield's persistent in-battle
    state sets (party-combat D-2): ``knocked_out`` holds the roster keys
    knocked out nonlethally at damage-commit time, so initiative, action
    provision, target selection, overwhelm classification, and terminal checks
    share one predicate instead of re-reading raw HP.

    ``tactical`` is the round execution context for the active round's
    round-start Defend/Dodge declarations (party-combat-defend-dodge). It is
    transient in-battle state, set and cleared by ``run_round`` inside one
    round; it is never a durable buff and never stacks across rounds.
    """

    teams: dict[str, frozenset[str]]
    roster: dict[str, Any]
    fled: set[str] = field(default_factory=set)
    knocked_out: set[str] = field(default_factory=set)
    tactical: "RoundTactical | None" = None

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

    def is_eligible(self, key: str) -> bool:
        """Whether one roster key is still a capable combatant this round.

        The single capability predicate initiative filtering, Taunt winner
        revalidation and session preflight all read, so a change to what
        "unable to act" means can never drift between them: the key is on the
        roster, has not fled, is not marked knocked out, and has stored HP
        above zero.
        """
        if key not in self.roster:
            return False
        return (
            key not in self.fled
            and not self.is_knocked_out(key)
            and _stored_hp(self.roster[key]) > 0
        )

    def taunt_winner(self, enemy_key: str) -> Any | None:
        """Return the active Taunt winner entity for one enemy, or ``None``.

        The winner was recorded on the round context at round start (the first
        taunter of that enemy in the round's own initiative sequence). It is
        revalidated live on every call: a winner no longer able to act --
        knocked out, defeated, fled, or absent from the roster -- has no active
        taunt, so the enemy is unrestricted for the remainder of the round and
        no losing taunter takes over. There is no taunt outside a round
        context, so ``None`` (every unrouted arena round) leaves selection
        byte-identical to the pre-taunt behaviour.
        """
        if self.tactical is None:
            return None
        winner_key = self.tactical.taunter_for(enemy_key)
        if winner_key is None or not self.is_eligible(winner_key):
            return None
        return self.roster[winner_key]


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
    the other stat's adjustment. The fold is
    :func:`world.rules.combat_modifiers.attack_with_bundle`, so a reader that
    already holds the effective stat applies the identical arithmetic.
    """
    return attack_with_bundle(
        float(entity.skills.effective_value(attack_key)),
        evaluate_combat_modifiers(entity),
        attack_key,
    )


def _adjusted_defense(entity: Any) -> float:
    """Return effective defense plus the flat ``defense`` bundle bonus."""
    return defense_with_bundle(
        float(entity.skills.effective_value("defense")),
        evaluate_combat_modifiers(entity),
    )


def roll_initiative(battlefield: Battlefield) -> list[str]:
    """Return living, active roster keys in descending initiative order."""
    weight = COMBAT_YAML["initiative"]["agility_weight"]
    scores = {
        key: entity.skills.effective_value("agility") * weight + roll_d100()
        for key, entity in battlefield.roster.items()
        if battlefield.is_eligible(key)
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
