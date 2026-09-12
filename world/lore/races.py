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
    """Independent combat-stat bands on the world's absolute scale.

    The fourth axis ``magic_power`` is the magic-school combat stat's
    species-wide floor-to-ceiling band (growth-redesign D2); it carries no
    progression semantics.
    """

    atk_phys: tuple[int, int]
    agility: tuple[int, int]
    defense: tuple[int, int]
    magic_power: tuple[int, int]


@dataclass(frozen=True)
class RaceProfile:
    """The load-bearing numeric profile shared by all race consumers."""

    key: str
    lifespan: tuple[int, int]
    vital_baseline: Vitals
    static_baseline: StaticBand
    learning_multiplier: float
    can_use_divine_arts: bool
    description: str


@dataclass(frozen=True)
class StaticTier:
    """A named physical-power band within a race.

    ``band`` remains the shared physical-power band applied to
    ``atk_phys``/``agility``/``defense``; ``magic_band`` is the tier's own
    deterministic ``magic_power`` floor-to-ceiling band, replacing the deleted
    race-level ``starting_magic_level`` as the source of tier-built NPC and
    profile magic power. It must be a subset of the owning race's
    ``static_baseline.magic_power`` band (validated at registry load).
    """

    key: str
    race_key: str
    display_name_zh: str
    order: int
    band: tuple[int, int | None]
    guild_rank_hint: str | None
    description: str
    magic_band: tuple[int, int]


@dataclass(frozen=True)
class StatModifiers:
    """Fractional distribution shifts that preserve aggregate physical power."""

    atk_phys: float = 0.0
    agility: float = 0.0
    defense: float = 0.0


@dataclass(frozen=True)
class Subrace:
    """An elf branch, a beastfolk subspecies, or a human bloodline subrace."""

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


def _static_band(
    lower: int, upper: int, magic_lower: int, magic_upper: int
) -> StaticBand:
    """Build one race's four-axis combat band (physical axes share one band)."""
    physical = (lower, upper)
    return StaticBand(
        atk_phys=physical,
        agility=physical,
        defense=physical,
        magic_power=(magic_lower, magic_upper),
    )


RACE_REGISTRY: dict[str, RaceProfile] = {
    "human": RaceProfile(
        key="human",
        lifespan=(60, 80),
        vital_baseline=Vitals(hp=(100, 200), mp=(100, 200), sp=(100, 200)),
        static_baseline=_static_band(1, 22, 5, 90),
        learning_multiplier=1.0,
        can_use_divine_arts=False,
        description="壽命短暫而繁衍迅速的人類，適應力強，是這片大陸最常見的種族。",
    ),
    "beastfolk": RaceProfile(
        key="beastfolk",
        lifespan=(50, 70),
        vital_baseline=Vitals(hp=(150, 200), mp=(30, 50), sp=(150, 200)),
        static_baseline=_static_band(4, 34, 1, 30),
        learning_multiplier=1.0,
        can_use_divine_arts=False,
        description="獸耳與尾巴的獸人族，體魄強健、感官敏銳，以部族文化與野性力量聞名。",
    ),
    "elf": RaceProfile(
        key="elf",
        lifespan=(800, 1200),
        vital_baseline=Vitals(
            hp=(10000, 10000), mp=(10000, 10000), sp=(10000, 10000)
        ),
        static_baseline=_static_band(70, 95, 100, 900),
        learning_multiplier=10.0,
        can_use_divine_arts=True,
        description="壽命數百年的精靈族，魔力深厚、體質超凡，與森林和魔法息息相關。",
    ),
}


STATIC_TIER_REGISTRY: dict[str, StaticTier] = {
    "human_commoner": StaticTier(
        "human_commoner", "human", "平民與非戰鬥者", 1, (1, 5), None,
        "Commoners and non-combatants.", (5, 20),
    ),
    "human_adventurer": StaticTier(
        "human_adventurer", "human", "一般冒險者", 2, (5, 9), "F",
        "General adventurers spanning guild ranks F through D.", (25, 35),
    ),
    "human_elite": StaticTier(
        "human_elite", "human", "精銳", 3, (7, 14), "C",
        "Elite fighters spanning guild ranks C through B.", (35, 55),
    ),
    "human_veteran": StaticTier(
        "human_veteran", "human", "一流", 4, (14, 18), "A",
        "First-rate human fighters associated with guild rank A.", (55, 72),
    ),
    "human_swordmaster": StaticTier(
        "human_swordmaster", "human", "大劍豪", 5, (18, 22), "S",
        "The absolute human ceiling, associated with guild rank S.", (72, 90),
    ),
    "beastfolk_juvenile": StaticTier(
        "beastfolk_juvenile", "beastfolk", "幼年與非戰鬥者", 1, (4, 8), None,
        "Juveniles and non-combatants.", (1, 8),
    ),
    "beastfolk_warrior": StaticTier(
        "beastfolk_warrior", "beastfolk", "一般部族戰士", 2, (10, 16), None,
        "The band containing most adult beastfolk warriors.", (8, 15),
    ),
    "beastfolk_city_apex": StaticTier(
        "beastfolk_city_apex", "beastfolk", "城級頂尖戰士", 3, (18, 24), None,
        "A top fighter of a tribal city, overlapping human swordmasters.", (15, 22),
    ),
    "beastfolk_tribal_apex": StaticTier(
        "beastfolk_tribal_apex", "beastfolk", "部族最強者、獸王級", 4, (26, 34), None,
        "One of the handful of strongest beastfolk alive.", (22, 30),
    ),
    "elf_common": StaticTier(
        "elf_common", "elf", "一般精靈", 1, (70, 95), None,
        "The physical band of a typical elf.", (100, 500),
    ),
    "elf_prodigy": StaticTier(
        "elf_prodigy", "elf", "精靈中的異數", 2, (95, None), None,
        "An exceptional elf with no documented hard ceiling.", (500, 900),
    ),
}


_ALL_ELEMENTS = ("fire", "water", "wind", "earth", "lightning", "ice", "light", "dark")

SUBRACE_REGISTRY: dict[str, Subrace] = {
    "human_royal": Subrace(
        "human_royal", "human", "王族", "王室血脈", None, None, (),
        "王都王室的血脈。自幼受統御與學識的教養，長於謀略而非武藝，魔力底蘊高於同族。",
        StatModifiers(-0.05, -0.05, 0.10), {"mp": (120, 220)},
    ),
    "human_noble": Subrace(
        "human_noble", "human", "貴族", "貴族血脈", None, None, (),
        "領地貴族的血脈。自幼習劍術與馬術，攻守取捨偏向進取。",
        StatModifiers(0.10, 0.05, -0.15),
    ),
    "human_coastal": Subrace(
        "human_coastal", "human", "濱海民", "濱海血脈", None, None, (),
        "世居港市與海岸的血脈。船上作業與碼頭往來練就輕捷身手，慣穿輕裝。",
        StatModifiers(0.05, 0.10, -0.15),
    ),
    "human_plains": Subrace(
        "human_plains", "human", "平原民", "平原血脈", None, None, (),
        "世居平原與城鎮的血脈。農耕與工坊並重，各項資質最為均衡。", StatModifiers(),
    ),
    "human_highland": Subrace(
        "human_highland", "human", "山地民", "山地血脈", None, None, (),
        "世居丘陵與谷地的血脈。礦坑與工坊的重勞動造就體魄與耐久，不以靈巧取勝。",
        StatModifiers(0.10, -0.15, 0.05),
    ),
    "fionnen": Subrace(
        "fionnen", "elf", "斐歐恩族", "森林精靈", 120, "village_fionnen",
        ("light",),
        "翠綠森林村的森林精靈。親和光屬性魔法，弓術與光法並修，從容而精準。",
        StatModifiers(),
    ),
    "ciaran": Subrace(
        "ciaran", "elf", "基亞蘭族", "黑暗精靈", 100, "village_ciaran",
        ("fire", "dark"),
        "暗影谷村的黑暗精靈。親和火與暗屬性魔法，刀術造詣尤深，攻勢凌厲。",
        StatModifiers(),
    ),
    "eolas": Subrace(
        "eolas", "elf", "伊歐拉斯族", "幻童精靈", 80, "village_eolas",
        _ALL_ELEMENTS,
        "幽月谷村的幻童精靈。外表永駐童年，親和所有屬性魔法，並擅長神之秘法。",
        StatModifiers(),
    ),
    "wolfkin": Subrace(
        "wolfkin", "beastfolk", "狼人族", "狼人", None, None, (),
        "群居狩獵的狼人，體格均衡而耐力出眾，慣於配合同伴作戰，無突出短板亦無驚人天賦。",
        StatModifiers(),
    ),
    "catkin": Subrace(
        "catkin", "beastfolk", "貓人族", "貓人", None, None, (),
        "身形輕盈、舉步無聲的貓人，敏捷遠出同族之上，代價是肌骨纖薄，難以吃下正面重創。",
        StatModifiers(-0.10, 0.40, -0.30),
    ),
    "bearkin": Subrace(
        "bearkin", "beastfolk", "熊人族", "熊人", None, None, (),
        "骨架厚重、力大無窮的熊人，慣用重型武器，卻因轉身遲鈍而追不上靈活的對手。",
        StatModifiers(0.45, -0.40, -0.05),
    ),
    "rabbitkin": Subrace(
        "rabbitkin", "beastfolk", "兔人族", "兔人", None, None, (),
        "奔躍如風的兔人，為獸人之中最快的亞種，擅長遊走遠射，卻經不起近身的一擊。",
        StatModifiers(-0.35, 0.50, -0.15),
    ),
    "bovinekin": Subrace(
        "bovinekin", "beastfolk", "牛人族", "牛人", None, None, (),
        "身軀如山、皮糙肉厚的牛人，防禦最厚而善於陣地戰，只因其行動緩慢而難以追擊機動的敵人。",
        StatModifiers(-0.10, -0.35, 0.45),
    ),
    "tigerkin": Subrace(
        "tigerkin", "beastfolk", "虎人族", "虎人", None, None, (),
        "爆發力驚人、攻速兼備的虎人，出擊凌厲而防禦為全亞種最弱，講求一擊制敵而非持久消耗。",
        StatModifiers(0.35, 0.10, -0.45),
    ),
    "foxkin": Subrace(
        "foxkin", "beastfolk", "狐人族", "狐人", None, None, (),
        "體格在獸人之中不突出的狐人，以體力換來同族最深厚的魔力底蘊，是最接近施法者的亞種。",
        StatModifiers(-0.05, 0.15, -0.10),
        {"mp": (50, 70)},
    ),
}


def _validate_static_tier_magic_bands(registry: dict[str, StaticTier]) -> None:
    """Reject a tier whose magic_band deviates from its owning race's band.

    Every ``StaticTier`` must reference a registered race and its closed
    ``magic_band`` must be a subset of that race's
    ``static_baseline.magic_power`` band (growth-redesign D2). A deviating
    tier fails the whole registry at import, exactly like the other
    fail-closed registry validations.
    """
    for tier_key, tier in registry.items():
        if tier.key != tier_key:
            raise ValueError(
                f"tier {tier_key!r} key mismatch (declared {tier.key!r})"
            )
        race = RACE_REGISTRY.get(tier.race_key)
        if race is None:
            raise ValueError(
                f"tier {tier_key!r} declares unknown race {tier.race_key!r}"
            )
        band = tier.magic_band
        if (
            not isinstance(band, tuple)
            or len(band) != 2
            or any(type(edge) is not int for edge in band)
            or band[0] > band[1]
        ):
            raise ValueError(
                f"tier {tier_key!r} magic_band must be a closed "
                f"non-decreasing integer tuple, got {band!r}"
            )
        race_band = race.static_baseline.magic_power
        if not (race_band[0] <= band[0] and band[1] <= race_band[1]):
            raise ValueError(
                f"tier {tier_key!r} magic_band {band} is outside race "
                f"{race.key!r} magic_power band {race_band}"
            )


_validate_static_tier_magic_bands(STATIC_TIER_REGISTRY)
