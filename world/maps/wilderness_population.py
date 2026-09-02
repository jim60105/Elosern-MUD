"""Deterministic wilderness monster population model and spawn service
(wilderness-monster-population).

A pure, closed-form coordinate-to-monster mapping mirrors the terrain model
(``region_for_coordinates`` / ``terrain_description``): the same large-hash
multipliers, no LLM, no RNG, no database reads. A guaranteed hunting band around
``capital_altoria``'s wilderness entry always hosts a low-tier monster, so the
introductory hunt (討伐低階魔物) is completable immediately after leaving the
North Gate.

``ensure_population`` is the idempotent spawn/respawn service and the sole
writer of wilderness monster presence. It registers created ``Monster`` objects
in the wilderness script's ``itemcoordinates`` (never room contents, which the
contrib's pooled-room design would strand), and it reconciles only monsters it
owns via the ``population_key`` marker so future scripted encounters, bosses,
or event content are never deleted, moved, or modified.
"""

from dataclasses import dataclass
from types import MappingProxyType

from evennia.utils.create import create_object

from world.observability import log_warn
from typeclasses.monsters import Monster
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.wilderness_provider import region_for_coordinates

# D-2 / wilderness-anchor-footprint: the entry coordinate is the capital's
# NORTH-GATE approach cell -- the exterior cell a traveler lands on leaving 北門
# toward the open wilderness -- read from the entry registry rather than
# duplicated (AGENTS.md: consumers read registry values). The old (60, 100) is
# now a footprint cell the provider refuses, so the hunting band recenters
# here; the introductory hunt stays reliably completable straight outside the
# North Gate. Read by both the model (band membership) and the tests.
_capital_entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
CAPITAL_ENTRY_XY = _capital_entry.approach_cell(_capital_entry.gate_for("s"))

# D-2: immutable region tables, covering every key of WILDERNESS_REGION_REGISTRY.
# MappingProxyType enforces the spec's "immutable mapping" contract at runtime,
# so a same-process consumer cannot silently rebalance the closed model.
_REGION_TIER = MappingProxyType({
    "western_hills_valleys": "low",
    "southwest_coast": "low",
    "southeast_coast": "low",
    "eastern_plains": "low",
    "northwest_highland_forest": "mid",
    "north_deep_forest": "high",
    "central_mountains": "high",
})

_REGION_DENSITY = MappingProxyType({
    "western_hills_valleys": 6,
    "southwest_coast": 3,
    "southeast_coast": 3,
    "eastern_plains": 3,
    "northwest_highland_forest": 7,
    "north_deep_forest": 8,
    "central_mountains": 8,
})

_HUNTING_BAND_DISTANCE = 3
_HASH_MULTIPLIER_X = 92821
_HASH_MULTIPLIER_Y = 68917


@dataclass(frozen=True)
class MonsterPopulation:
    """One deterministic monster the wilderness hosts at a coordinate."""

    tier: str
    name_zh: str


def _coordinate_hash(x: int, y: int) -> int:
    """Return the closed-form coordinate hash shared with the terrain model."""
    return x * _HASH_MULTIPLIER_X + y * _HASH_MULTIPLIER_Y


def _in_hunting_band(x: int, y: int) -> bool:
    """Return whether ``(x, y)`` is within Chebyshev distance 3 of the entry."""
    entry_x, entry_y = CAPITAL_ENTRY_XY
    return max(abs(x - entry_x), abs(y - entry_y)) <= _HUNTING_BAND_DISTANCE


def population_for_coordinates(x: int, y: int) -> MonsterPopulation | None:
    """Return the deterministic monster population at ``(x, y)``, or ``None``.

    Pure closed-form arithmetic on the two coordinates alone -- no database
    read, no RNG, no wall-clock input. Coordinates inside the hunting
    band around ``CAPITAL_ENTRY_XY`` are always present at ``low`` tier;
    elsewhere presence is ``(x * 92821 + y * 68917) % 10 < density`` and the
    name is ``(x * 92821 + y * 68917) % len(example_monsters_zh)`` on every
    branch, hunting band included.
    """
    if _in_hunting_band(x, y):
        tier = "low"
    else:
        region = region_for_coordinates(x, y)
        tier = _REGION_TIER[region]
        if _coordinate_hash(x, y) % 10 >= _REGION_DENSITY[region]:
            return None
    examples = MONSTER_TIER_REGISTRY[tier].example_monsters_zh
    return MonsterPopulation(tier, examples[_coordinate_hash(x, y) % len(examples)])


def _population_key(x: int, y: int) -> str:
    """Return the ownership marker this service stamps on every created monster."""
    return f"wilderness:{x}:{y}"


def _stored_hp(monster: Monster) -> float:
    """Read the monster's stored HP without advancing a wall-clock gauge."""
    from world.rules.action import _stored_trait_value

    return _stored_trait_value(monster.traits.hp)


def _remove_monster(wilderness, monster: Monster) -> None:
    """Pop ``monster`` from the wilderness bookkeeping and delete it."""
    wilderness.db.itemcoordinates.pop(monster, None)
    monster.delete()


def _spawn(wilderness, coordinates: tuple[int, int], expected: MonsterPopulation) -> None:
    """Create one fresh population monster registered at ``coordinates``."""
    x, y = coordinates
    monster = create_object(Monster, key=expected.name_zh)
    monster.threat_tier = expected.tier
    monster.apply_monster_tier("floor")
    monster.db.population_key = _population_key(x, y)
    wilderness.db.itemcoordinates[monster] = coordinates
    room = wilderness.db.rooms.get(coordinates)
    if room is not None:
        monster.location = room


def _matches_expected(monster: Monster, expected: MonsterPopulation) -> bool:
    """Return whether ``monster`` is a living, model-conformant population entry.

    The idempotency special case requires not just any living marker-matching
    monster but one that still matches the model -- so a tier or name that no
    longer matches (after a model or registry fix) is reconciled rather than
    kept stale. Compare the monster's stored tier and its key against the
    expected population to close the drift gap.
    """
    return (
        _stored_hp(monster) > 0
        and monster.threat_tier == expected.tier
        and monster.key == expected.name_zh
    )


def _session_participant_ids() -> frozenset[int]:
    """Return the dbrefs referenced by any persisted active combat session.

    Defense in depth for ``ensure_population`` (fix-startup-session-restore-
    order D2): scans every ``PlayerCharacter``'s persisted ``active_combat``
    record and collects its participant dbrefs, so reconciliation can leave
    session-referenced monsters untouched. Records that cannot be parsed are
    skipped -- their dbrefs are unknown, so they protect nothing and the
    startup restore step handles them separately.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.combat_session import from_storage

    participants: set[int] = set()
    for player in PlayerCharacter.objects.all_family():
        raw = player.db.active_combat
        if raw is None:
            continue
        try:
            record = from_storage(dict(raw))
        except Exception as error:
            log_warn(
                "combat_session_payload_unparseable_skip",
                exc=error,
                context={"char": player.key or str(player.pk), "key": "active_combat"},
            )
            continue
        participants.update(record.player_ids)
        participants.update(record.enemy_ids)
    return frozenset(participants)


def ensure_population(wilderness, coordinates: tuple[int, int]) -> None:
    """Reconcile one wilderness coordinate against its deterministic population.

    Only ``Monster`` objects bearing the matching ``population_key`` marker are
    ever reconciled. When a persisted active combat session references any
    marker-matching monster, the whole pass is skipped so the participant is
    neither deleted nor respawned before session restoration settles it
    (fix-startup-session-restore-order D2). When the model returns ``None``,
    every marker-matching monster is deleted (stale-cleanup); foreign monsters
    are untouched. When it
    returns a population, the coordinate is reconciled to exactly one living,
    model-conformant marker-matching monster: if exactly one such monster
    already exists (living, correct tier, correct key) nothing is written;
    otherwise every marker-matching monster (dead, surplus, or stale) is removed
    and one fresh ``Monster`` is created with its tier applied, the marker set,
    registration in ``itemcoordinates``, and its location attached to the room
    currently active at that coordinate, if any.
    """
    x, y = coordinates
    expected = population_for_coordinates(x, y)
    key = _population_key(x, y)
    matching = [
        obj
        for obj in wilderness.get_objs_at_coordinates(coordinates)
        if isinstance(obj, Monster) and obj.db.population_key == key
    ]
    if matching:
        participants = _session_participant_ids()
        if any(monster.pk in participants for monster in matching):
            # A persisted active combat session still references one of these
            # monsters; skip the whole reconciliation pass so the participant
            # is neither deleted nor respawned before session restoration
            # settles it.
            return
    if expected is None:
        for monster in matching:
            _remove_monster(wilderness, monster)
        return
    if len(matching) == 1 and _matches_expected(matching[0], expected):
        # Idempotency special case (D-3): exactly one living, model-conformant
        # marker-matching monster already exists, so no write happens.
        return
    for monster in matching:
        _remove_monster(wilderness, monster)
    _spawn(wilderness, coordinates, expected)
