"""Monster species and variant registries (monster-data-model design §2-§3).

The approved first bestiary batch (``docs/lore/bestiary.md``, content-approved
2026-10-05) as read-only lore data: six frozen ``MonsterSpecies`` rows and
twelve frozen ``MonsterVariant`` rows, keyed by stable keys, validated while
the module-level registries are built (design D-S2: an authored typo fails at
import, so no consumer can observe a half-valid registry).

The layering is deliberately additive. ``world.lore.monsters``'s
``MONSTER_TIER_REGISTRY`` stays the coarse threat classification it has always
been; species identity is layered beside it, and this change re-points no
caller. Everything downstream (individual construction, placement, quest
selectors, species art identity) is owned by sibling changes that read these
registries.

Two boundaries are pinned here and must not be blurred:

* **Balance honesty (design D-S4).** ``combat_profile`` is either ``None`` or a
  complete frozen :class:`MonsterCombatProfile`; ``danger_grade`` is either
  ``None`` or an authored guild danger grade. The bestiary approves narrative
  only, so every shipped row carries both as ``None``. ``None`` means "no
  approved per-variant profile exists" — never a zero, never a number inferred
  from flavoured names, and never tier-band truth.
* **Abilities are narrative (design D-S5, requirement R4).** The six approved
  special abilities have no executable form: this module registers no skill
  key, behaviour profile, or combat trait for them, and adds no placeholder
  field that could stand in for one. Their mechanics are a named external
  prerequisite owned by the skill/behaviour-mechanics work; the approved prose
  (including its stated limits) lives in the published narrative fields only.

Key grammar (requirement R1) is the shared stable-key contract, whose predicate
lives in ``world/art/subjects.py``. ``world/lore/`` may not import that module —
``world/art/fallback_keys.py`` documents the boundary ("lore must never import
the rest of ``world.art``"), and ``subjects.py`` imports ``world.lore`` back, so
a lore-side import would be a cycle hazard. The contract is therefore applied
:func:`validate_monster_species_registry`'s injectable ``key_violation_face``:
shipped construction passes no face (no rule text is duplicated here), and the
registered data-contract test
``world/lore/tests/test_monster_species_content.py`` passes the real shared
predicate, so every shipped key is validated by the one shared implementation.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType

from .guild import GUILD_RANK_REGISTRY
from .monsters import MONSTER_TIER_REGISTRY
from .wilderness_regions import WILDERNESS_REGION_REGISTRY


class MonsterSpeciesRegistryError(ValueError):
    """A species or variant registry row violates the registry contract."""


# The completeness sentinel of :class:`MonsterCombatProfile`: a field left at
# this value means the authored profile omitted it, which is a construction
# error rather than a silently defaulted number (requirement R3's "partial
# profile is rejected" — never a zero, never an inferred value).
_INCOMPLETE = object()


@dataclass(frozen=True, slots=True)
class MonsterCombatProfile:
    """One complete authored numeric combat profile (design §3).

    All-or-nothing by construction: every one of the seven values must be an
    explicit non-negative integer literal.
    """

    hp: int = _INCOMPLETE
    mp: int = _INCOMPLETE
    sp: int = _INCOMPLETE
    atk_phys: int = _INCOMPLETE
    agility: int = _INCOMPLETE
    defense: int = _INCOMPLETE
    magic_power: int = _INCOMPLETE

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is _INCOMPLETE or value is None:
                raise MonsterSpeciesRegistryError(
                    f"combat profile field {field.name!r} is unpopulated; a "
                    "profile carries a complete value set or does not exist"
                )
            if isinstance(value, bool) or not isinstance(value, int):
                raise MonsterSpeciesRegistryError(
                    f"combat profile field {field.name!r} must be an integer "
                    f"literal, got {value!r}"
                )
            if value < 0:
                raise MonsterSpeciesRegistryError(
                    f"combat profile field {field.name!r} must not be negative, "
                    f"got {value!r}"
                )


@dataclass(frozen=True, slots=True)
class MonsterSpecies:
    """One species: stable identity plus the approved published narrative.

    ``habitat_tags`` are habitat compatibility only (requirement R5): no
    function in this module decides a spawn, placement, respawn, or quantity
    from them. ``default_variant_key`` names the species' baseline ordinary
    variant, which is where the species' ability baseline lives — no ability
    field exists on this class, so a species and its default variant cannot
    disagree about one. ``ordinary_variant`` is the species-level statement of
    design §3's ordinary-vs-stronger axis (the species baseline registered here
    is an ordinary version); the authoritative per-variant classification
    remains ``MonsterVariant.ordinary_variant``.
    """

    key: str
    display_name_zh: str
    published_description_zh: str
    published_appearance_zh: str
    published_ecology_zh: str
    habitat_tags: tuple[str, ...]
    author_hidden_truth_zh: str
    author_explanation_zh: str
    author_conjecture_zh: str
    default_variant_key: str
    ordinary_variant: bool


@dataclass(frozen=True, slots=True)
class MonsterVariant:
    """One complete standalone variant; no parent, no override chain.

    ``threat_tier`` is the coarse band of ``MONSTER_TIER_REGISTRY`` and never
    substitutes for identity (requirement R2). Every record is complete on its
    own: nothing merges values from the species row.
    """

    key: str
    species_key: str
    display_name_zh: str
    description_zh: str
    threat_tier: str
    ordinary_variant: bool
    combat_profile: MonsterCombatProfile | None
    danger_grade: str | None


def _faces(habitat_face, tier_face, grade_face) -> tuple[frozenset, frozenset, frozenset]:
    """Resolve the validated vocabularies, defaulting to the static lore faces."""
    return (
        frozenset(habitat_face) if habitat_face is not None else frozenset(WILDERNESS_REGION_REGISTRY),
        frozenset(tier_face) if tier_face is not None else frozenset(MONSTER_TIER_REGISTRY),
        frozenset(grade_face) if grade_face is not None else frozenset(GUILD_RANK_REGISTRY),
    )


def build_monster_variant_registry(
    declarations: Iterable[MonsterVariant],
) -> dict[str, MonsterVariant]:
    """Merge declared variants into the keyed registry, rejecting key theft.

    A variant key names exactly one owner: a second declaration of the same key
    for a *different* species is a cross-species key collision and fails at
    construction (requirement R2), never overwriting the first owner silently.
    """
    registry: dict[str, MonsterVariant] = {}
    owners: dict[str, str] = {}
    for variant in declarations:
        owner = owners.get(variant.key)
        if owner is not None and owner != variant.species_key:
            raise MonsterSpeciesRegistryError(
                f"variant key {variant.key!r} is already owned by species "
                f"{owner!r}; {variant.species_key!r} cannot register it again"
            )
        owners[variant.key] = variant.species_key
        registry[variant.key] = variant
    return registry


def _check_key(
    mapping_key: object,
    record_key: object,
    what: str,
    key_violation_face: Callable[[object], str | None] | None,
) -> None:
    """Reject a key that is not the stable identity of its own record."""
    if not isinstance(record_key, str) or not record_key:
        raise MonsterSpeciesRegistryError(
            f"{what} {mapping_key!r} has no stable non-empty key"
        )
    if record_key != mapping_key:
        raise MonsterSpeciesRegistryError(
            f"{what} key {record_key!r} does not match its registry key "
            f"{mapping_key!r}"
        )
    if key_violation_face is not None:
        violation = key_violation_face(record_key)
        if violation is not None:
            raise MonsterSpeciesRegistryError(
                f"{what} key {record_key!r} violates the shared stable-key "
                f"contract ({violation})"
            )


def validate_monster_species_registry(
    species: Mapping[str, MonsterSpecies],
    variants: Mapping[str, MonsterVariant],
    *,
    key_violation_face: Callable[[object], str | None] | None = None,
    habitat_face: Iterable[str] | None = None,
    tier_face: Iterable[str] | None = None,
    grade_face: Iterable[str] | None = None,
) -> None:
    """Raise :class:`MonsterSpeciesRegistryError` unless every row is valid.

    Pure and DB-free, mirroring ``world/lore/wilderness_entry.py``'s
    ``validate_wilderness_entries`` shape: the module-level registries are
    validated through this one function while they are built, so a malformed
    authored row can never be observed by a consumer.

    ``key_violation_face`` is the shared stable-key contract's predicate
    (``world.art.subjects.subject_key_violation``). It stays optional because
    ``world/lore/`` may not import ``world.art`` (see the module docstring);
    the registered data-contract test supplies it so the shipped keys are
    validated by the one shared implementation. The three vocabulary faces
    default to the static lore registries and are injectable so behavior tests
    can exercise this function with invented keys.

    The cross-species variant-key collision rule is not enforced here: a keyed
    mapping cannot express two owners of one key, so it is enforced where the
    registry is merged (:func:`build_monster_variant_registry`). Validation
    only reads its inputs and raises before anything is published.
    """
    habitat_keys, tier_keys, grade_keys = _faces(habitat_face, tier_face, grade_face)

    for mapping_key, row in species.items():
        _check_key(mapping_key, row.key, "species", key_violation_face)
    for mapping_key, row in variants.items():
        _check_key(mapping_key, row.key, "variant", key_violation_face)

    for mapping_key, row in species.items():
        if not isinstance(row.display_name_zh, str) or not row.display_name_zh:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} has no display name"
            )
        if not isinstance(row.default_variant_key, str) or not row.default_variant_key:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} declares no default variant"
            )
        if not isinstance(row.ordinary_variant, bool):
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} must author its ordinary/stronger "
                "classification as a boolean"
            )
        if not row.habitat_tags:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} declares no habitat compatibility tags"
            )
        for tag in row.habitat_tags:
            if not isinstance(tag, str) or not tag:
                raise MonsterSpeciesRegistryError(
                    f"species {mapping_key!r} has an empty habitat tag"
                )
            if tag not in habitat_keys:
                raise MonsterSpeciesRegistryError(
                    f"species {mapping_key!r} habitat tag {tag!r} is not a "
                    "known habitat"
                )

    for mapping_key, row in variants.items():
        if row.species_key not in species:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares unknown species "
                f"{row.species_key!r}"
            )
        if not isinstance(row.threat_tier, str) or row.threat_tier not in tier_keys:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares unknown threat tier "
                f"{row.threat_tier!r}"
            )
        if not isinstance(row.ordinary_variant, bool):
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} must author its ordinary/stronger "
                "classification as a boolean"
            )
        if row.combat_profile is not None and not isinstance(
            row.combat_profile, MonsterCombatProfile
        ):
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} carries a non-record combat profile"
            )
        if row.danger_grade is not None and row.danger_grade not in grade_keys:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares unknown guild danger grade "
                f"{row.danger_grade!r}"
            )

    for mapping_key, row in species.items():
        default = variants.get(row.default_variant_key)
        if default is None:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} default variant "
                f"{row.default_variant_key!r} is not registered"
            )
        if default.species_key != mapping_key:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} default variant "
                f"{row.default_variant_key!r} belongs to species "
                f"{default.species_key!r}"
            )
        if not default.ordinary_variant:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} default variant "
                f"{row.default_variant_key!r} is a stronger variant; a species "
                "baseline must be an ordinary variant"
            )
        if row.ordinary_variant is not default.ordinary_variant:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} classifies itself as ordinary="
                f"{row.ordinary_variant!r} while its default variant "
                f"{row.default_variant_key!r} is ordinary="
                f"{default.ordinary_variant!r}"
            )


# --------------------------------------------------------------------------
# The approved first bestiary batch (docs/lore/bestiary.md, approved
# 2026-10-05). Display/description prose is the approved zh-TW narrative; the
# published appearance excerpt is the same approved sentence's physical clause.
# Author-private notes are reasoned from the bestiary's own usage boundary
# (in-world origins stay unknown): the hidden-truth field records that no
# origin truth is authored, the explanation field carries the authoring
# rationale, and the conjecture field keeps an unverified in-world claim
# explicitly marked as unverified.
# --------------------------------------------------------------------------

_SPECIES_DECLARATIONS: tuple[MonsterSpecies, ...] = (
    MonsterSpecies(
        "sway_whistle_sparrow",
        "穗鳴雀",
        "麻雀類的小型群居鳥，生活於東部平原的田埂、灌木與收穫後的農地。",
        "麻雀類的小型群居鳥。",
        "啄食成熟穀物前，族群會發出短促而整齊的鳴聲，接著以微弱風屬性氣流震落乾燥穀粒。"
        "穗間響起的沙沙聲，是農民辨認牠們的線索。"
        "牠們造成的麻煩集中於收穫期；田地仍能正常耕作，但反覆造訪的族群會損耗尚未收起的穀物。"
        "濕穀與牢固的未熟穗不易受影響。"
        "牠們無法掀翻糧車、吹倒作物，也不具備大範圍風暴能力。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種在世界設定中沒有已定的起源真相；設計刻意不記載創造者、"
        "魔力污染或迷宮成因，任何此類說法都只是世界內未經證實的猜想。",
        "（作者私有：作者解釋）作為收穫期的低階麻煩來源，示範能力邊界如何限制風屬性生態而"
        "不授予任何可執行技能；棲地相容性指向東部平原。",
        "（作者私有：尚未證實的猜想）農戶之間流傳牠們受穀倉殘留魔力吸引，但沒有可查證的紀錄。",
        "grain_pecker",
        True,
    ),
    MonsterSpecies(
        "tide_lamp_crab",
        "潮燈蟹",
        "近岸蟹類，棲息於兩側海岸的礁隙、潮池與港外灘地。",
        "近岸蟹類。",
        "背甲上的發光斑紋會追隨附近燈光的明暗節奏。"
        "沿岸居民知道牠們會聚集在魔法燈附近，漁人偶爾將牠們當成潮池的位置標記。"
        "大量聚集時，不熟悉港口的小船可能誤判岸邊訊號；靠近礁洞的人也可能受到螯足攻擊。"
        "牠們只能重現已有光源的節奏，不能製造幻覺或偽裝物體。"
        "發光不等於治療能力，也不表示牠們掌握光屬性治療術。",
        ("southeast_coast", "southwest_coast"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；發光斑紋的成因在設定中保持未記載。",
        "（作者私有：作者解釋）低階物種的第二個方向：以既有光源為條件的辨識干擾，"
        "刻意排除幻覺與治療語意。",
        "（作者私有：尚未證實的猜想）漁村傳說牠們是某位失蹤燈匠的遺留造物，僅見於口述。",
        "shore_walker",
        True,
    ),
    MonsterSpecies(
        "ridge_burrow_hare",
        "築埂兔",
        "穴居兔類，生活於平原邊緣與丘陵的鬆土帶。",
        "穴居兔類。",
        "牠們以土屬性力量壓實巢壁，將挖出的土築成低矮環埂。"
        "居民從一圈圈異常牢固的小土埂辨認巢穴；普通雨水不容易沖散，因此棄置巢穴也會留下痕跡。"
        "族群沿灌溉渠築巢時，土埂可能堵住分水口，坑洞則妨礙農具與牲畜通行。"
        "牠們只能處理巢穴周圍的鬆土，無法鑽穿岩盤、城牆或石造基礎。"
        "洞道提供正常的逃離路線，不構成瞬間移動。",
        ("eastern_plains", "western_hills_valleys"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；土屬性力量的來源不在設定中交代。",
        "（作者私有：作者解釋）以地形改造描述低階危害（分水口堵塞、通行妨礙），"
        "不附帶任何戰鬥或控場能力。",
        "（作者私有：尚未證實的猜想）部分居民相信土埂是牠們的集體記憶痕跡，這種說法未經檢驗。",
        "burrow_maker",
        True,
    ),
    MonsterSpecies(
        "rock_echo_goat",
        "岩響山羊",
        "山羊類魔獸，生活於西部丘陵的岩坡、偏遠採石地與山麓。",
        "山羊類魔獸。",
        "牠們落足前會用角敲擊岩面，辨認裂隙與鬆動岩層。"
        "遇到威脅時，可以沿接觸的岩面傳出土屬性脈動，使原本已鬆動的碎石滑落。"
        "採石工人會留意牠們的敲岩聲，因為族群常出現在不穩定岩坡附近；"
        "牠們占據狹窄運料路線時，便形成難以繞過的威脅。"
        "脈動無法粉碎完整岩盤，不會造成大範圍地震。"
        "地形與既有鬆石是能力成立的重要條件，不能將牠們描述為隨處都能引發同等規模的崩塌。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；敲岩與脈動的來源不在設定中交代。",
        "（作者私有：作者解釋）中階物種示範地形依賴型能力：威力取決於既有鬆石，"
        "作為配置與評級理由的素材。",
        "（作者私有：尚未證實的猜想）採石業者謠傳牠們的敲擊聲能預言崩塌，因果未經證實。",
        "cliff_stepper",
        True,
    ),
    MonsterSpecies(
        "fog_mane_lynx",
        "霧鬃山貓",
        "山貓類的獨居獵食者，活動於西北高地森林與潮濕山谷。",
        "山貓類的獨居獵食者。",
        "頸側長毛隨牠引動的微弱氣流展開，使既有霧氣沿身側聚集，干擾獵物判斷接近方向。"
        "牠主要捕食林中動物；部分個體會在晨霧中跟隨馱獸隊伍，等待落單動物，"
        "因此與部族獵人及山道運輸發生衝突。"
        "能力依賴既有霧氣，乾燥、無霧的環境中優勢大幅減弱。"
        "牠仍有足跡、氣味與聲音，不能完全隱形、製造任意幻覺或瞬間移動。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；聚霧能力的來源不在設定中交代。",
        "（作者私有：作者解釋）以環境條件（霧氣）限定優勢，作為中階獵食者的敘事邊界，"
        "避免隱形與瞬間移動。",
        "（作者私有：尚未證實的猜想）部族獵人相信牠們聽得懂人語，這種說法交代不出任何證據。",
        "wood_stalker",
        True,
    ),
    MonsterSpecies(
        "tide_devouring_crocodile",
        "吞潮鱷",
        "大型鱷類，棲息於東南部偏遠河口、濕地與潮汐支流。",
        "大型鱷類。",
        "牠在接觸活物時，可以透過水屬性力量吸取對方的部分魔力。"
        "施法者與牠纏鬥時，可能先感到魔力消耗異常，再發現危險。"
        "牠仍依靠咬合與伏擊捕食，並非遠距離施法者。"
        "能力需要近身接觸，不能隔著整條河抽取魔力，也不會把吸取的魔力轉成傷口治療。"
        "此處的吸取對應可消耗的魔力資源，不表示永久降低目標的固定 magic_power。"
        "具體消耗量與技能效果不在本次核准範圍內。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；吸取魔力的成因不在設定中交代。",
        "（作者私有：作者解釋）展示資源壓力型危害（魔力消耗）而不實作機制，"
        "並明確標記數值與技能效果不在核准範圍內。",
        "（作者私有：尚未證實的猜想）渡運站傳說河口鱷群受沉沒魔法器物吸引，沒有實地證實。",
        "bank_lurker",
        True,
    ),
)

_VARIANT_DECLARATIONS: tuple[MonsterVariant, ...] = (
    MonsterVariant(
        "grain_pecker",
        "sway_whistle_sparrow",
        "啄穗型",
        "普通版本，分散覓食。",
        "low",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "flock_leader",
        "sway_whistle_sparrow",
        "領群型",
        "以鳴聲協調同伴，從不同方向干擾驅趕者。",
        "low",
        False,
        None,
        None,
    ),
    MonsterVariant(
        "shore_walker",
        "tide_lamp_crab",
        "灘行型",
        "普通版本，遇人多半退避。",
        "low",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "reef_warden",
        "tide_lamp_crab",
        "守礁型",
        "占據狹窄洞口，利用地形保護族群。",
        "low",
        False,
        None,
        None,
    ),
    MonsterVariant(
        "burrow_maker",
        "ridge_burrow_hare",
        "掘巢型",
        "普通版本，依靠洞道逃避。",
        "low",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "nest_guard",
        "ridge_burrow_hare",
        "護巢型",
        "加固入口，在窄處阻擋侵入者。",
        "low",
        False,
        None,
        None,
    ),
    MonsterVariant(
        "cliff_stepper",
        "rock_echo_goat",
        "踏崖型",
        "普通版本，偏向逃往高處。",
        "mid",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "pass_warden",
        "rock_echo_goat",
        "守隘型",
        "守住岩坡入口，將衝撞與落石結合。",
        "mid",
        False,
        None,
        None,
    ),
    MonsterVariant(
        "wood_stalker",
        "fog_mane_lynx",
        "林伏型",
        "普通版本，守候林間獵徑。",
        "mid",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "trail_hunter",
        "fog_mane_lynx",
        "獵道型",
        "反覆試探隊伍邊緣，避免正面接近完整隊列。",
        "mid",
        False,
        None,
        None,
    ),
    MonsterVariant(
        "bank_lurker",
        "tide_devouring_crocodile",
        "潛岸型",
        "普通版本，守候野生動物渡水處。",
        "mid",
        True,
        None,
        None,
    ),
    MonsterVariant(
        "bay_warden",
        "tide_devouring_crocodile",
        "守灣型",
        "占據有遮蔽的泊岸入口，阻礙小船靠岸。",
        "mid",
        False,
        None,
        None,
    ),
)

_MONSTER_SPECIES_ROWS: dict[str, MonsterSpecies] = {
    row.key: row for row in _SPECIES_DECLARATIONS
}
_MONSTER_VARIANT_ROWS: dict[str, MonsterVariant] = build_monster_variant_registry(
    _VARIANT_DECLARATIONS
)

# Shipped content must be valid the moment the module loads (titles.py
# precedent): validation runs here, before either registry is published, so an
# authored typo cannot produce a partially valid registry. The shared
# stable-key predicate is deliberately not imported here (see the module
# docstring); the registered data-contract test re-runs this same validation
# with `key_violation_face=subject_key_violation`, which is where the shipped
# keys are checked against the one shared implementation.
validate_monster_species_registry(_MONSTER_SPECIES_ROWS, _MONSTER_VARIANT_ROWS)

# The published registries are read-only proxies: every consumer reads through
# `.get` / `values()` / `[key]` / `in`, and no subsystem may mutate lore data
# in place.
MONSTER_SPECIES_REGISTRY: MappingProxyType = MappingProxyType(_MONSTER_SPECIES_ROWS)
MONSTER_VARIANT_REGISTRY: MappingProxyType = MappingProxyType(_MONSTER_VARIANT_ROWS)


def published_species_view(species: MonsterSpecies) -> dict[str, object]:
    """The player-facing projection of one species: an allowlist, never a dump.

    Enumerated explicitly (design D-S6) so serialization can never grow an
    author-private field when a field is added. ``author_hidden_truth_zh``,
    ``author_explanation_zh`` and ``author_conjecture_zh`` are absent by
    construction; a missing published prose field stays empty and is never
    backfilled from private text.
    """
    return {
        "key": species.key,
        "display_name_zh": species.display_name_zh,
        "published_description_zh": species.published_description_zh,
        "published_appearance_zh": species.published_appearance_zh,
        "published_ecology_zh": species.published_ecology_zh,
        "habitat_tags": species.habitat_tags,
    }


def published_variant_view(variant: MonsterVariant) -> dict[str, object]:
    """The player-facing projection of one variant (an allowlist, design D-S6)."""
    profile = variant.combat_profile
    return {
        "key": variant.key,
        "species_key": variant.species_key,
        "display_name_zh": variant.display_name_zh,
        "description_zh": variant.description_zh,
        "threat_tier": variant.threat_tier,
        "ordinary_variant": variant.ordinary_variant,
        "combat_profile": (
            None
            if profile is None
            else {
                "hp": profile.hp,
                "mp": profile.mp,
                "sp": profile.sp,
                "atk_phys": profile.atk_phys,
                "agility": profile.agility,
                "defense": profile.defense,
                "magic_power": profile.magic_power,
            }
        ),
        "danger_grade": variant.danger_grade,
    }
