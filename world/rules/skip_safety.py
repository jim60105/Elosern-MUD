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
    """Register a transient battlefield lookup for its current roster.

    Indexed by each participant's immutable dbref so same-key entities can
    never cross-evict each other's registrations.
    """
    _BATTLEFIELDS.update({str(entity.pk): battlefield for entity in battlefield.roster.values()})


def unregister_active_battlefield(entity: Any) -> None:
    """Remove one combatant's transient battlefield lookup on settlement."""
    _BATTLEFIELDS.pop(str(entity.pk), None)


def unregister_participants(dbrefs: Iterable[int]) -> None:
    """Remove every registration whose roster contains any participant dbref.

    Settlement cleanup for a session whose participant objects cannot all be
    resolved (party-combat D-5): a deleted participant's dbref still maps to a
    live battlefield in the registry, so this scan purges the whole session's
    registrations at once, and a stale registration can never survive to block
    a later object that reuses the same display key.
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
    return _BATTLEFIELDS.get(str(actor.pk))


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
