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
    emphasis: str
    background: str

    def allocation_dict(self) -> dict[str, int]:
        """Return a mutable copy suitable for rules validation."""
        return dict(self.allocations)


PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    "human_wanderer": PlayerPreset(
        "human_wanderer", "艾琳", 24, 24, "human", None,
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11)),
        "生命力與魔力均衡的開局配點",
        "來自南境的年輕旅人，追逐著地圖邊緣未標記的空白。",
    ),
    "foxkin_scout": PlayerPreset(
        "foxkin_scout", "露芙", 22, 22, "beastfolk", "foxkin",
        (("hp", 25), ("mp", 10), ("sp", 25), ("atk_phys", 15),
         ("agility", 15), ("defense", 15)),
        "敏捷與近身作戰優先的斥候配點",
        "身手矯健的狐人斥候，習慣在隊伍前方探路。",
    ),
    "elf_guardian": PlayerPreset(
        "elf_guardian", "瑟芮雅", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13)),
        "防禦與均衡戰技優先的守護者配點",
        "斐歐恩森林出身的精靈護衛，以長壽的眼光看待短暫的人類王國。",
    ),
}
