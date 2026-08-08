"""Deterministic safety checks for explicit time skips."""

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from typeclasses.monsters import Monster
from world.rules.combat import Battlefield, is_battle_over


class SkipRejectReason(StrEnum):
    IN_COMBAT = "in_combat"
    HOSTILE_PRESENT = "hostile_present"


_BATTLEFIELDS: dict[str, Battlefield] = {}


def register_active_battlefield(battlefield: Battlefield) -> None:
    """Register a transient battlefield lookup for its current roster."""
    _BATTLEFIELDS.update({key: battlefield for key in battlefield.roster})


def unregister_active_battlefield(entity: Any) -> None:
    """Remove one combatant's transient battlefield lookup on settlement."""
    _BATTLEFIELDS.pop(str(entity.key), None)


def unregister_participants(dbrefs: Iterable[int]) -> None:
    """Remove every registration whose roster contains any participant dbref.

    Settlement cleanup for a session whose participant objects cannot all be
    resolved (party-combat D-5): a deleted participant's key can no longer be
    looked up through its object, but its battlefield registration still holds
    every roster key -- so this scan purges the whole session's keys at once,
    and a stale key can never survive to block a later object that reuses it.
    """
    wanted = {int(dbref) for dbref in dbrefs}
    stale = [
        key
        for key, battlefield in _BATTLEFIELDS.items()
        if any(
            isinstance(getattr(entity, "pk", None), int)
            and int(entity.pk) in wanted
            for entity in battlefield.roster.values()
        )
    ]
    for key in stale:
        _BATTLEFIELDS.pop(key, None)


def _active_battlefield_for(actor: Any) -> Battlefield | None:
    return _BATTLEFIELDS.get(str(actor.key))


def _living(entity: Any) -> bool:
    return getattr(getattr(entity, "traits", None), "hp", None) is not None and entity.traits.hp.value > 0


def evaluate_skip_safety(actor: Any) -> SkipRejectReason | None:
    """Reject only active combat and a co-located living monster."""
    battlefield = _active_battlefield_for(actor)
    actor_key = str(actor.key)
    if (
        battlefield is not None
        and actor_key in battlefield.roster
        and actor_key not in battlefield.fled
        and _living(actor)
        and not is_battle_over(battlefield)
    ):
        return SkipRejectReason.IN_COMBAT
    location = getattr(actor, "location", None)
    for occupant in getattr(location, "contents", ()):
        if isinstance(occupant, Monster) and _living(occupant):
            return SkipRejectReason.HOSTILE_PRESENT
    return None
