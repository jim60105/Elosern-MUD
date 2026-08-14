"""Race registries from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vitals:
    """Baseline-to-gifted bands for resource pools."""

    hp: tuple[int, int]
    mp: tuple[int, int]
    sp: tuple[int, int]


@dataclass(frozen=True)
class StaticBand:
    """Independent physical-stat bands on the world's absolute scale."""

    atk_phys: tuple[int, int]
    agility: tuple[int, int]
    defense: tuple[int, int]


@dataclass(frozen=True)
class RaceProfile:
    """The load-bearing numeric profile shared by all race consumers."""

    key: str
    lifespan: tuple[int, int]
    magic_cap: int
    starting_magic_level: int
    vital_baseline: Vitals
    static_baseline: StaticBand
    learning_multiplier: float
    can_use_divine_arts: bool
    description: str


@dataclass(frozen=True)
class StaticTier:
    """A named physical-power band within a race."""

    key: str
    race_key: str
    display_name_zh: str
    order: int
    band: tuple[int, int | None]
    guild_rank_hint: str | None
    description: str


@dataclass(frozen=True)
class StatModifiers:
    """Fractional distribution shifts that preserve aggregate physical power."""

    atk_phys: float = 0.0
    agility: float = 0.0
    defense: float = 0.0


@dataclass(frozen=True)
class Subrace:
    """An elf branch or beastfolk subspecies."""

    key: str
    race_key: str
    display_name_zh: str
    common_name_zh: str
    population: int | None
    home_anchor_key: str | None
    affinity_elements: tuple[str, ...]
    specialty: str
    static_modifiers: StatModifiers
    vital_overrides: dict[str, tuple[int, int]] | None = None


def _static_band(lower: int, upper: int) -> StaticBand:
    band = (lower, upper)
    return StaticBand(atk_phys=band, agility=band, defense=band)


RACE_REGISTRY: dict[str, RaceProfile] = {
    "human": RaceProfile(
        key="human",
        lifespan=(60, 80),
        magic_cap=90,
        starting_magic_level=30,
        vital_baseline=Vitals(hp=(100, 200), mp=(100, 200), sp=(100, 200)),
        static_baseline=_static_band(1, 22),
        learning_multiplier=1.0,
        can_use_divine_arts=False,
        description="壽命短暫而繁衍迅速的人類，適應力強，是這片大陸最常見的種族。",
    ),
    "beastfolk": RaceProfile(
        key="beastfolk",
        lifespan=(50, 70),
        magic_cap=30,
        starting_magic_level=10,
        vital_baseline=Vitals(hp=(150, 200), mp=(30, 50), sp=(150, 200)),
        static_baseline=_static_band(4, 34),
        learning_multiplier=1.0,
        can_use_divine_arts=False,
        description="獸耳與尾巴的獸人族，體魄強健、感官敏銳，以部族文化與野性力量聞名。",
    ),
    "elf": RaceProfile(
        key="elf",
        lifespan=(800, 1200),
        magic_cap=900,
        starting_magic_level=300,
        vital_baseline=Vitals(
            hp=(10000, 10000), mp=(10000, 10000), sp=(10000, 10000)
        ),
        static_baseline=_static_band(70, 95),
        learning_multiplier=10.0,
        can_use_divine_arts=True,
        description="壽命數百年的精靈族，魔力深厚、體質超凡，與森林和魔法息息相關。",
    ),
}


STATIC_TIER_REGISTRY: dict[str, StaticTier] = {
    "human_commoner": StaticTier(
        "human_commoner", "human", "平民與非戰鬥者", 1, (1, 5), None,
        "Commoners and non-combatants.",
    ),
    "human_adventurer": StaticTier(
        "human_adventurer", "human", "一般冒險者", 2, (5, 9), "F",
        "General adventurers spanning guild ranks F through D.",
    ),
    "human_elite": StaticTier(
        "human_elite", "human", "精銳", 3, (7, 14), "C",
        "Elite fighters spanning guild ranks C through B.",
    ),
    "human_veteran": StaticTier(
        "human_veteran", "human", "一流", 4, (14, 18), "A",
        "First-rate human fighters associated with guild rank A.",
    ),
    "human_swordmaster": StaticTier(
        "human_swordmaster", "human", "大劍豪", 5, (18, 22), "S",
        "The absolute human ceiling, associated with guild rank S.",
    ),
    "beastfolk_juvenile": StaticTier(
        "beastfolk_juvenile", "beastfolk", "幼年與非戰鬥者", 1, (4, 8), None,
        "Juveniles and non-combatants.",
    ),
    "beastfolk_warrior": StaticTier(
        "beastfolk_warrior", "beastfolk", "一般部族戰士", 2, (10, 16), None,
        "The band containing most adult beastfolk warriors.",
    ),
    "beastfolk_city_apex": StaticTier(
        "beastfolk_city_apex", "beastfolk", "城級頂尖戰士", 3, (18, 24), None,
        "A top fighter of a tribal city, overlapping human swordmasters.",
    ),
    "beastfolk_tribal_apex": StaticTier(
        "beastfolk_tribal_apex", "beastfolk", "部族最強者、獸王級", 4, (26, 34), None,
        "One of the handful of strongest beastfolk alive.",
    ),
    "elf_common": StaticTier(
        "elf_common", "elf", "一般精靈", 1, (70, 95), None,
        "The physical band of a typical elf.",
    ),
    "elf_prodigy": StaticTier(
        "elf_prodigy", "elf", "精靈中的異數", 2, (95, None), None,
        "An exceptional elf with no documented hard ceiling.",
    ),
}


_ALL_ELEMENTS = ("fire", "water", "wind", "earth", "lightning", "ice", "light", "dark")

SUBRACE_REGISTRY: dict[str, Subrace] = {
    "human_royal": Subrace(
        "human_royal", "human", "王族", "皇族與大貴族", None, None, (),
        "Royal blood and high-noble upbringing; education over combat.",
        StatModifiers(-0.05, -0.05, 0.10), {"mp": (120, 220)},
    ),
    "human_noble": Subrace(
        "human_noble", "human", "貴族", "中小貴族", None, None, (),
        "Minor nobility such as 侍從貴族 (薇歐蕾特's attendant 莉茲婭).",
        StatModifiers(0.10, 0.05, -0.15),
    ),
    "human_wealthy": Subrace(
        "human_wealthy", "human", "富裕平民", "商人與高階冒險者", None, None, (),
        "Wealthy commoners: big merchants, senior adventurers, mages.",
        StatModifiers(0.05, 0.10, -0.15),
    ),
    "human_commoner": Subrace(
        "human_commoner", "human", "平民", "普通平民", None, None, (),
        "Ordinary commoners: artisans, shopkeepers, adventurers.", StatModifiers(),
    ),
    "human_laborer": Subrace(
        "human_laborer", "human", "底層平民", "農民與勞工", None, None, (),
        "The lower class: farmers and laborers.", StatModifiers(0.10, -0.15, 0.05),
    ),
    "fionnen": Subrace(
        "fionnen", "elf", "斐歐恩族", "森林精靈", 120, "village_fionnen",
        ("light",), "Excels at archery and light magic.", StatModifiers(),
    ),
    "ciaran": Subrace(
        "ciaran", "elf", "基亞蘭族", "黑暗精靈", 100, "village_ciaran",
        ("fire", "dark"), "Excels at blade arts and fire and dark magic.", StatModifiers(),
    ),
    "eolas": Subrace(
        "eolas", "elf", "伊歐拉斯族", "幻童精靈", 80, "village_eolas",
        _ALL_ELEMENTS, "Excels at all elements and divine arts.", StatModifiers(),
    ),
    "wolfkin": Subrace(
        "wolfkin", "beastfolk", "狼人族", "狼人", None, None, (),
        "Balanced fighters who excel in team combat.", StatModifiers(),
    ),
    "catkin": Subrace(
        "catkin", "beastfolk", "貓人族", "貓人", None, None, (),
        "Agile assassins and scouts.", StatModifiers(-0.10, 0.40, -0.30),
    ),
    "bearkin": Subrace(
        "bearkin", "beastfolk", "熊人族", "熊人", None, None, (),
        "Powerful heavy-weapon fighters.", StatModifiers(0.45, -0.40, -0.05),
    ),
    "rabbitkin": Subrace(
        "rabbitkin", "beastfolk", "兔人族", "兔人", None, None, (),
        "The fastest beastfolk and skilled archers.", StatModifiers(-0.35, 0.50, -0.15),
    ),
    "bovinekin": Subrace(
        "bovinekin", "beastfolk", "牛人族", "牛人", None, None, (),
        "Defensive fighters suited to holding ground.", StatModifiers(-0.10, -0.35, 0.45),
    ),
    "tigerkin": Subrace(
        "tigerkin", "beastfolk", "虎人族", "虎人", None, None, (),
        "Fast, aggressive fighters with low defense.", StatModifiers(0.35, 0.10, -0.45),
    ),
    "foxkin": Subrace(
        "foxkin", "beastfolk", "狐人族", "狐人", None, None, (),
        "Mediocre physical fighters with stronger magical aptitude.",
        StatModifiers(-0.05, 0.15, -0.10),
        {"mp": (50, 70)},
    ),
}
