"""Magic registries from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MagicTier:
    key: str
    display_name_zh: str
    level_min: int
    level_max: int | None
    example_spells_zh: tuple[str, ...]
    description: str


MAGIC_TIER_REGISTRY: dict[str, MagicTier] = {
    "apprentice": MagicTier(
        "apprentice", "初級", 0, 15,
        ("火球", "水箭", "風刃", "治癒術", "身體強化"),
        "Basic practical magic.",
    ),
    "intermediate": MagicTier(
        "intermediate", "中級", 16, 30,
        ("火焰風暴", "冰牆", "飛行術"),
        "Useful intermediate magic.",
    ),
    "advanced": MagicTier(
        "advanced", "高級", 31, 70,
        ("熔岩術", "暴風雪", "高級治癒", "統御術"),
        "Powerful advanced magic.",
    ),
    "superior": MagicTier(
        "superior", "超級", 71, 90,
        ("龍炎術", "地震術", "神聖光輝"),
        "Strategic magic reached by very few humans.",
    ),
    "ultimate": MagicTier(
        "ultimate", "究極", 91, None, (),
        "Legendary magic almost impossible for humans to master.",
    ),
}
