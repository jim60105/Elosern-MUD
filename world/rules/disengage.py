"""Universal combat disengagement resolved through the action pipeline."""

from typing import Any

from world.rules import combat
from world.rules.action import (
    PendingEffect,
    RejectReason,
    RejectedAction,
    register_effect_handler,
)
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.dice import roll_d100
from world.skills.handler import INNATE_SKILL_KEYS
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


FLEE_SKILL_KEY = "flee"

if FLEE_SKILL_KEY not in INNATE_SKILL_KEYS:
    raise RuntimeError("flee must remain an innate skill")

SKILL_REGISTRY[FLEE_SKILL_KEY] = SkillDef(
    key=FLEE_SKILL_KEY,
    label="逃跑",
    description="嘗試脫離當前戰鬥。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    faction_constraint=FactionConstraint.SELF_ONLY,
    cost={},
    usable_out_of_combat=False,
    element=None,
    effects=["disengage:self"],
)


def _adjusted_agility(entity: Any) -> float:
    """Return effective agility with only the shared agility modifier applied."""
    modifiers = evaluate_combat_modifiers(entity)
    return combat._apply_percent_mod(
        float(entity.skills.effective_value("agility")),
        modifiers.get("agility"),
    )


def _fastest_pursuer_agility(
    battlefield: combat.Battlefield,
    actor: Any,
) -> float | None:
    """Return the fastest living, present member of the opposing team.

    Knocked-out members are excluded through the shared predicate, so an
    inactive floored companion never keeps a fleeing monster (or player) from
    an automatic success (party-combat D-2).
    """
    actor_team = battlefield.team_of(str(actor.key))
    values = [
        _adjusted_agility(battlefield.roster[key])
        for team, members in battlefield.teams.items()
        if team != actor_team
        for key in members
        if key in battlefield.roster
        and key not in battlefield.fled
        and not battlefield.is_knocked_out(key)
        and combat._stored_hp(battlefield.roster[key]) > 0
    ]
    return max(values, default=None)


def _attempt_flee(
    actor: Any,
    battlefield: combat.Battlefield,
) -> tuple[bool, dict[str, float | int | None]]:
    """Roll one agility contest without mutating encounter state."""
    actor_agility = _adjusted_agility(actor)
    pursuer_agility = _fastest_pursuer_agility(battlefield, actor)
    raw_roll = None
    if pursuer_agility is None:
        success = True
    else:
        raw_roll = roll_d100()
        success = (
            raw_roll + actor_agility
            >= combat.COMBAT_YAML["to_hit"]["defender_constant"]
            + pursuer_agility
        )
    return success, {
        "roll": raw_roll,
        "actor_agility": actor_agility,
        "pursuer_agility": pursuer_agility,
    }


def _noop() -> None:
    """Commit-time no-op for a failed disengagement attempt."""


def _handle_disengage(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    event_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage one battlefield-level flee outcome."""
    battlefield = event_context.get("battlefield")
    if battlefield is None:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "flee: event_context missing required 'battlefield' key",
        )
    success, detail = _attempt_flee(actor, battlefield)
    description = "|".join(
        (
            "disengage_attempt",
            str(actor.key),
            str(int(success)),
            "none" if detail["roll"] is None else str(detail["roll"]),
            f"{detail['actor_agility']:g}",
            (
                "none"
                if detail["pursuer_agility"] is None
                else f"{detail['pursuer_agility']:g}"
            ),
        )
    )
    return [
        PendingEffect(
            entity=battlefield,
            description=description,
            surfaces=frozenset(),
            apply=(
                lambda: battlefield.fled.add(str(actor.key))
                if success
                else _noop()
            ),
        )
    ]


register_effect_handler(
    "disengage",
    _handle_disengage,
    surfaces=frozenset({"battlefield"}),
    requires_event_context=frozenset({"battlefield"}),
)
