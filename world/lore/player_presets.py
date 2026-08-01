"""Immutable starter characters offered during account registration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerPreset:
    """A complete player-owned identity and raw stat allocation."""

    key: str
    display_name: str
    age: int
    apparent_age: int
    race: str
    subrace: str | None
    allocations: tuple[tuple[str, int], ...]

    def allocation_dict(self) -> dict[str, int]:
        """Return a mutable copy suitable for rules validation."""
        return dict(self.allocations)


PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    "human_wanderer": PlayerPreset(
        "human_wanderer", "艾琳", 24, 24, "human", None,
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11)),
    ),
    "foxkin_scout": PlayerPreset(
        "foxkin_scout", "露芙", 22, 22, "beastfolk", "foxkin",
        (("hp", 25), ("mp", 10), ("sp", 25), ("atk_phys", 15),
         ("agility", 15), ("defense", 15)),
    ),
    "elf_guardian": PlayerPreset(
        "elf_guardian", "瑟芮雅", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13)),
    ),
}
