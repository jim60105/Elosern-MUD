"""Deterministic NPC/display-name rollers over the frozen lore corpus.

Pure-logic module (npc-namegen-rules-roller, design D1): no database access,
no Evennia imports, no module-level or global RNG. Every random decision goes
through the caller-injected ``rng`` so consumers own the replay strategy —
the creation dice inject an unseeded ``Random`` instance while the NPC flow
injects a crc32-seeded one for blueprint-rebuild reproducibility.

Registry reads target the frozen constants of ``world.lore.names``; testability
never relies on patching them (empty-pool fallback tests call ``_roll_from_pack``
with synthetic ``NamePack`` values, fallback-candidate tests drive
``_pick_pack_for_race`` with a recording RNG).
"""

from random import Random

from world.lore.names import (
    NAME_PACK_BY_RACE,
    NAME_PACK_REGISTRY,
    NamePack,
    compose_display_name,
)

# sex -> given-name pool (design D2). Values outside this table — including
# "" and None — are treated exactly like an unspecified sex: pick a pool at
# random. Validation belongs to the entry points, not this layer.
_SEX_POOL = {"female": "f", "male": "m", "other": "u"}

_GIVEN_POOLS = ("m", "f", "u")

# Random race fallback candidates: the sorted distinct bound packs (design D4).
# Sorting decouples rng.choice indices from the mapping's literal insertion
# order; dwarf/halfling are absent from the mapping values and never participate.
_BOUND_PACK_KEYS = tuple(sorted(set(NAME_PACK_BY_RACE.values())))


def _roll_from_pack(pack: NamePack, sex: str | None, rng: Random) -> str:
    """Roll one display name from one pack; core takes a value, not a key (D3).

    An empty sex-filtered pool falls back to the pack's full given pool so the
    generator never dies; the surname pool is not sex-filtered and needs none.
    """

    # Non-str values (even unhashable ones) join the unspecified path: this
    # layer validates nothing and must never die on a caller's bad input.
    pool_key = _SEX_POOL.get(sex) if isinstance(sex, str) else None
    if pool_key is None:
        pool_key = rng.choice(_GIVEN_POOLS)
    parts = pack.given[pool_key]
    if not parts:
        parts = pack.given["m"] + pack.given["f"] + pack.given["u"]
    given = rng.choice(parts)
    surname = rng.choice(pack.surnames)
    return compose_display_name(given, surname)


def roll_name(pack_key: str, sex: str | None, rng: Random) -> str:
    """Roll 「given.zh・surname.zh」 from one named pack.

    An unknown ``pack_key`` propagates ``KeyError`` unchanged (design D5):
    callers pass program constants, and swallowing the error would ship a
    wrong-corpus name straight into the player's view.
    """

    return _roll_from_pack(NAME_PACK_REGISTRY[pack_key], sex, rng)


def _pick_pack_for_race(race_key: str | None, rng: Random) -> NamePack:
    """Resolve the pack for a race, falling back to a random bound pack (D4)."""

    pack_key = NAME_PACK_BY_RACE.get(race_key)
    if pack_key is not None:
        return NAME_PACK_REGISTRY[pack_key]
    return NAME_PACK_REGISTRY[rng.choice(_BOUND_PACK_KEYS)]


def roll_name_for_race(race_key: str | None, sex: str | None, rng: Random) -> str:
    """Roll a display name for a race key; None/unknown → random bound pack."""

    return _roll_from_pack(_pick_pack_for_race(race_key, rng), sex, rng)


__all__ = ["roll_name", "roll_name_for_race"]
