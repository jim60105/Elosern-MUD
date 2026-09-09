"""Monster threat registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass

from world.art.fallback_keys import validate_fallback_key

from .races import StaticBand


@dataclass(frozen=True)
class MonsterTier:
    key: str
    display_name_zh: str
    guild_rank_range: tuple[str, str]
    static_band: StaticBand
    hp_band: tuple[int, int]
    example_monsters_zh: tuple[str, ...]
    description: str
    # The OPTIONAL built-in gallery fallback key (gallery-builtin-fallbacks).
    # A threat tier MAY claim one key of the closed vocabulary for its
    # generic-monster subject; the unset default means the subject resolves
    # ``monster_anon`` by rule. Validated at registry construction below.
    fallback_key: str | None = None


def _static_band(lower: int, upper: int) -> StaticBand:
    band = (lower, upper)
    return StaticBand(
        atk_phys=band,
        agility=band,
        defense=band,
        # Monster magic power is documented nowhere in lore; every tier
        # carries the zero band so monster construction reads the fourth
        # axis deterministically without inventing a value (D-A2).
        magic_power=(0, 0),
    )


MONSTER_TIER_REGISTRY: dict[str, MonsterTier] = {
    "low": MonsterTier(
        "low", "低階", ("F", "E"), _static_band(3, 8), (50, 150),
        ("史萊姆", "哥布林", "巨鼠"),
        "Threats a beginning adventurer can handle alone.",
    ),
    "mid": MonsterTier(
        "mid", "中階", ("D", "C"), _static_band(12, 20), (200, 400),
        ("狼型魔獸", "食人魔", "地龍"),
        "Threats requiring a party of ordinary adventurers.",
    ),
    "high": MonsterTier(
        "high", "高階", ("B", "A"), _static_band(22, 35), (400, 700),
        ("雙頭龍", "魔法生物", "巨魔"),
        "Threats matching or exceeding the finest human fighters.",
    ),
    "calamity": MonsterTier(
        "calamity", "災厄級", ("S", "S"), _static_band(60, 150), (1200, 3000),
        ("古龍", "魔神", "災獸"),
        "Legendary threats beyond the human scale and above a typical elf.",
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
