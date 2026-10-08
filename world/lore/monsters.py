"""Monster threat registry from design section 5.1 and lore-world-data.

A threat tier is the coarse threat classification (monster-data-model design
§3) and stays exactly that: this module is unchanged by the species registry,
which lives beside it in ``world.lore.monster_species`` and carries the stable
species/variant identity plus the approved bestiary narrative.
"""

from dataclasses import dataclass

from world.art.fallback_keys import validate_fallback_key

@dataclass(frozen=True)
class MonsterStaticBand:
    """Independent monster axes; None is an open upper authoring bound."""

    atk_phys: tuple[int, int | None]
    agility: tuple[int, int | None]
    defense: tuple[int, int | None]
    magic_power: tuple[int, int | None]


@dataclass(frozen=True)
class MonsterTier:
    key: str
    display_name_zh: str
    guild_rank_range: tuple[str, str]
    static_band: MonsterStaticBand
    hp_band: tuple[int, int | None]
    example_monsters_zh: tuple[str, ...]
    description: str
    # The OPTIONAL built-in gallery fallback key (gallery-builtin-fallbacks).
    # A threat tier MAY claim one key of the closed vocabulary for its
    # generic-monster subject; the unset default means the subject resolves
    # ``monster_anon`` by rule. Validated at registry construction below.
    fallback_key: str | None = None


def _static_band(attack, agility, defense) -> MonsterStaticBand:
    return MonsterStaticBand(
        atk_phys=attack,
        agility=agility,
        defense=defense,
        # Monster magic power is documented nowhere in lore; every tier
        # carries the zero band so monster construction reads the fourth
        # axis deterministically without inventing a value (D-A2).
        magic_power=(0, 0),
    )


MONSTER_TIER_REGISTRY: dict[str, MonsterTier] = {
    "low": MonsterTier(
        "low", "低階", ("F", "E"), _static_band((3, 12), (3, 12), (2, 8)), (25, 70),
        ("史萊姆", "哥布林", "巨鼠"),
        "Threats a beginning adventurer can handle alone.",
    ),
    "mid": MonsterTier(
        "mid", "中階", ("D", "C"), _static_band((18, 28), (10, 24), (10, 16)), (110, 230),
        ("狼型魔獸", "食人魔", "地龍"),
        "Threats requiring a party of ordinary adventurers.",
    ),
    "high": MonsterTier(
        "high", "高階", ("B", "A"), _static_band((26, 40), (16, 30), (18, 32)), (300, 750),
        ("雙頭龍", "魔法生物", "巨魔"),
        "Threats matching or exceeding the finest human fighters.",
    ),
    "calamity": MonsterTier(
        "calamity", "災厄級", ("S", "S"), _static_band((60, None), (60, None), (60, None)), (1200, None),
        ("古龍", "魔神", "災獸"),
        "Open-ended legendary threats; 3000 HP and 150 physical stats are references.",
    ),
}


def _validate_monster_fallback_keys(registry: dict[str, MonsterTier]) -> None:
    """Reject a declared fallback key outside the closed vocabulary.

    Runs at registry construction (import) time so an authored typo fails
    loudly at import rather than silently resolving to a nonexistent image.
    """
    for tier in registry.values():
        validate_fallback_key(tier.fallback_key, f"monster tier {tier.key!r}")


_validate_monster_fallback_keys(MONSTER_TIER_REGISTRY)
