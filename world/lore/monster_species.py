"""Monster species and variant registries (monster-data-model design §2-§3).

The authored bestiary (``docs/lore/bestiary.md``) as read-only lore data:
one frozen ``MonsterSpecies`` row per authored species and one frozen
``MonsterVariant`` row per authored variant,
keyed by stable keys, validated while the module-level registries are built
(design D-S2: an authored typo fails at import, so no consumer can observe a
half-valid registry). Registry membership is the content authority: nothing
here enumerates an approved key list, and adding, renaming or retiring a row
is a data edit rather than a requirement change.

The layering is deliberately additive. ``world.lore.monsters``'s
``MONSTER_TIER_REGISTRY`` stays the coarse threat classification it has always
been; species identity is layered beside it, and this change re-points no
caller. Everything downstream (individual construction, placement, quest
selectors, species art identity) is owned by sibling changes that read these
registries.

Two boundaries are pinned here and must not be blurred:

* **Profile obligation (design D-S4).** ``combat_profile`` is either ``None``
  or a complete frozen :class:`MonsterCombatProfile`; ``danger_grade`` is
  either ``None`` or an authored guild danger grade. Whether a variant
  *requires* a populated profile and grade is that row's own authored
  declaration, :attr:`MonsterVariant.profile_required`: a required row rejects
  absence at load, and an optional row keeps the documented tier-band fallback
  of individual construction. ``None`` means "no authored per-variant profile"
  — never a zero, never a number inferred from a flavoured name, prose or
  another variant, and never tier-band truth.
* **Abilities are narrative until a species' mechanics land (design D-S5).**
  Delivery follows the authored kit data and nothing else: a variant declaring
  active/passive skill keys or a behaviour profile is executable through the
  shared engine, and one declaring none registers no skill key, behaviour
  profile or combat trait, with no placeholder field standing in for one.
  There is no species allowlist: every delivered kit is delivered because its
  row declares it. The authored prose
  (including its stated limits) lives in the narrative fields only.

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
from dataclasses import dataclass, field, fields
from types import MappingProxyType

from .guild import GUILD_RANK_REGISTRY
from .monsters import MONSTER_TIER_REGISTRY, MonsterTier
from .registry_refs import ref


#: The longest species, variant or site individual name, in code points: the
#: longest name the presence rail and the figure plate render without an
#: ellipsis (monster-individual-names). Registry validation enforces it.
MONSTER_NAME_MAX_CODE_POINTS = 5


class MonsterSpeciesRegistryError(ValueError):
    """A species or variant registry row violates the registry contract."""


# The completeness sentinel of :class:`MonsterCombatProfile`: a field left at
# this value means the authored profile omitted it, which is a construction
# error rather than a silently defaulted number — never a zero, never an
# inferred value.
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
    default_variant_key: str = field(
        metadata=ref("monster_variants", inverse="default_of_species")
    )
    ordinary_variant: bool


@dataclass(frozen=True, slots=True)
class MonsterVariant:
    """One complete standalone variant; no parent, no override chain.

    ``threat_tier`` is the coarse band of ``MONSTER_TIER_REGISTRY`` and never
    substitutes for identity. Every record is complete on its own: nothing
    merges values from the species row.

    ``profile_required`` is the variant's own authored profile obligation, not
    another key list: a required row must carry a complete ``combat_profile``
    and a ``danger_grade`` (validated at load), while an optional row may omit
    both and keep the documented individual-construction tier-band fallback.
    It is a plain declared field, so completeness can never silently become
    optional by omission.
    """

    key: str
    species_key: str = field(metadata=ref("monster_species", inverse="variants"))
    display_name_zh: str
    description_zh: str
    threat_tier: str = field(metadata=ref("monster_tiers", inverse="variants"))
    ordinary_variant: bool
    combat_profile: MonsterCombatProfile | None
    danger_grade: str | None
    profile_required: bool
    active_skill_keys: tuple[str, ...] = ()
    passive_skill_keys: tuple[str, ...] = ()
    behaviour_profile_key: str | None = None


def _faces(habitat_face, tier_face, grade_face):
    """Resolve the validated vocabularies, defaulting to the static lore faces.

    The habitat vocabulary is a map-owned declaration (the continent's terrain
    regions), so it has no import-time lore face: the published geography
    validates every habitat tag against the regions it declares. An explicit
    ``habitat_face`` still checks membership for behavior tests.
    """
    return (
        frozenset(habitat_face) if habitat_face is not None else None,
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


#: HP, attack, agility, defense, magic, then ordered guild-rank endpoints.
_MonsterBound = tuple[int, int | None]
_TierBandRow = tuple[
    _MonsterBound, _MonsterBound, _MonsterBound, _MonsterBound,
    _MonsterBound, tuple[str, str],
]


def _default_tier_band_face(
    tiers: Mapping[str, MonsterTier] | None = None,
) -> dict[str, _TierBandRow]:
    """Project independent axes without imposing a physical symmetry."""
    face: dict[str, _TierBandRow] = {}
    for key, tier in (MONSTER_TIER_REGISTRY if tiers is None else tiers).items():
        face[key] = (
            tier.hp_band,
            tier.static_band.atk_phys,
            tier.static_band.agility,
            tier.static_band.defense,
            tier.static_band.magic_power,
            tier.guild_rank_range,
        )
    return face


def _grade_positions(grade_face: Iterable[str] | None) -> dict[str, int]:
    """The rank order a danger grade is judged by inside a rank range.

    The membership question ("is this a known grade?") is answered by
    :func:`_faces` with a frozenset, which carries no order. The order lives in
    the shipped guild rank registry's authored ``order`` field, or — for an
    injected vocabulary, which is what behavior tests use — in the sequence the
    face is given in, so invented ranks carry invented positions. A grade or a
    rank-range endpoint the resolved vocabulary does not carry has no order,
    and callers reject it rather than guessing one.
    """
    if grade_face is None:
        return {
            rank.key: rank.order
            for rank in sorted(
                GUILD_RANK_REGISTRY.values(), key=lambda rank: rank.order
            )
        }
    return {key: position for position, key in enumerate(grade_face)}


def _check_profile_bands(
    mapping_key: str,
    profile: MonsterCombatProfile,
    tier_key: str,
    bands: _TierBandRow,
) -> None:
    """Reject a profile value outside the band of the tier it declares.

    Bounds are inclusive at both ends, so a value exactly on a band edge is
    inside it. MP and SP are deliberately not checked: the tier model declares
    no pool band, so there is no tier truth to compare a pool against, and
    inventing one would be unapproved balance content. The shipped zeros are
    pinned by the approved-literal contract instead.
    """
    hp_band, attack_band, agility_band, defense_band, magic_band, _rank_range = bands
    for axis, value, band in (
        ("hp", profile.hp, hp_band),
        ("atk_phys", profile.atk_phys, attack_band),
        ("agility", profile.agility, agility_band),
        ("defense", profile.defense, defense_band),
        ("magic_power", profile.magic_power, magic_band),
    ):
        if value < band[0] or (band[1] is not None and value > band[1]):
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares {axis} {value} outside its "
                f"threat tier {tier_key!r} band {band}; a combat profile must "
                "lie inside the band of the tier it declares"
            )


def _check_grade_band(
    mapping_key: str,
    grade: str,
    tier_key: str,
    rank_range: tuple[str, str],
    positions: Mapping[str, int],
) -> None:
    """Reject a danger grade outside the tier's guild rank range.

    The grade is judged by its order inside the range, never by membership in
    a set of keys, so a range wider than two ranks admits every rank between
    its endpoints. The lookup is total: the caller has already rejected a grade
    outside the grade vocabulary, and the positions are that same vocabulary's
    order.
    """
    for endpoint in rank_range:
        if endpoint not in positions:
            raise MonsterSpeciesRegistryError(
                f"threat tier {tier_key!r} declares guild rank range "
                f"{rank_range!r} naming unknown rank {endpoint!r}"
            )
    bounds = [positions[endpoint] for endpoint in rank_range]
    if not min(bounds) <= positions[grade] <= max(bounds):
        raise MonsterSpeciesRegistryError(
            f"variant {mapping_key!r} declares danger grade {grade!r} outside "
            f"its threat tier {tier_key!r} guild rank range {rank_range!r}"
        )


def validate_monster_species_registry(
    species: Mapping[str, MonsterSpecies],
    variants: Mapping[str, MonsterVariant],
    *,
    key_violation_face: Callable[[object], str | None] | None = None,
    habitat_face: Iterable[str] | None = None,
    tier_face: Iterable[str] | None = None,
    grade_face: Iterable[str] | None = None,
    tier_band_face: Mapping[str, _TierBandRow] | None = None,
) -> None:
    """Raise :class:`MonsterSpeciesRegistryError` unless every row is valid.

    Pure and DB-free, mirroring the shared core map diagnostics' validate-
    before-publication shape: the module-level registries are validated through
    this one function while they are built, so a malformed authored row can
    never be observed by a consumer.

    ``key_violation_face`` is the shared stable-key contract's predicate
    (``world.art.subjects.subject_key_violation``). It stays optional because
    ``world/lore/`` may not import ``world.art`` (see the module docstring);
    the registered data-contract test supplies it so the shipped keys are
    validated by the one shared implementation. The three vocabulary faces
    default to the static lore registries and are injectable so behavior tests
    can exercise this function with invented keys.

    ``tier_band_face`` answers the band question: it maps a threat tier key to
    that tier's ``(hp, attack, agility, defense, magic, guild_rank_range)`` and
    defaults to ``MONSTER_TIER_REGISTRY``'s own bands. Every variant's declared
    tier must be present in the face — a tier it does not carry raises the
    named error instead of skipping the check, so no rating can ever arrive
    with no band to be judged against — and a variant that carries a
    ``combat_profile`` or a ``danger_grade`` is then judged against that row:
    every value inside its band with both bounds inclusive, and the grade by
    its order inside the tier's guild rank range. MP and SP have no band here,
    for the reason :func:`_check_profile_bands` records.

    ``profile_required`` is a typed obligation, not a second key list: a
    variant that does not declare it as a boolean is rejected, and a variant
    declaring it ``True`` must carry both a ``combat_profile`` and a
    ``danger_grade``. A variant declaring it ``False`` may carry neither, or
    either, and what it does carry is still shape- and band-checked above.

    The cross-species variant-key collision rule is not enforced here: a keyed
    mapping cannot express two owners of one key, so it is enforced where the
    registry is merged (:func:`build_monster_variant_registry`). Validation
    only reads its inputs and raises before anything is published.
    """
    # The grade face is materialized once: the membership vocabulary and the
    # rank order are two readings of the same vocabulary, and a single-use
    # iterable would leave the second reading empty.
    grade_sequence = None if grade_face is None else tuple(grade_face)
    habitat_keys, tier_keys, grade_keys = _faces(
        habitat_face, tier_face, grade_sequence
    )
    grade_positions = _grade_positions(grade_sequence)
    tier_bands = (
        _default_tier_band_face() if tier_band_face is None else tier_band_face
    )

    for mapping_key, row in species.items():
        _check_key(mapping_key, row.key, "species", key_violation_face)
    for mapping_key, row in variants.items():
        _check_key(mapping_key, row.key, "variant", key_violation_face)

    for mapping_key, row in species.items():
        if not isinstance(row.display_name_zh, str) or not row.display_name_zh:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} has no display name"
            )
        if len(row.display_name_zh) > MONSTER_NAME_MAX_CODE_POINTS:
            raise MonsterSpeciesRegistryError(
                f"species {mapping_key!r} display name exceeds "
                f"{MONSTER_NAME_MAX_CODE_POINTS} code points"
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
            if habitat_keys is not None and tag not in habitat_keys:
                raise MonsterSpeciesRegistryError(
                    f"species {mapping_key!r} habitat tag {tag!r} is not a "
                    "known habitat"
                )

    for mapping_key, row in variants.items():
        if not isinstance(row.display_name_zh, str) or not row.display_name_zh:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} has no display name"
            )
        if len(row.display_name_zh) > MONSTER_NAME_MAX_CODE_POINTS:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} display name exceeds "
                f"{MONSTER_NAME_MAX_CODE_POINTS} code points"
            )
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
        if not isinstance(row.profile_required, bool):
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} must declare its combat-profile "
                f"obligation as a boolean, got {row.profile_required!r}"
            )
        if row.profile_required and row.combat_profile is None:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares a required combat profile "
                "but carries none"
            )
        if row.profile_required and row.danger_grade is None:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares a required combat profile "
                "but declares no danger grade"
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
        bands = tier_bands.get(row.threat_tier)
        if bands is None:
            raise MonsterSpeciesRegistryError(
                f"variant {mapping_key!r} declares threat tier "
                f"{row.threat_tier!r}, which the band face does not carry; a "
                "rating would have no band to be judged against"
            )
        if row.combat_profile is not None:
            _check_profile_bands(
                mapping_key, row.combat_profile, row.threat_tier, bands
            )
        if row.danger_grade is not None:
            _check_grade_band(
                mapping_key,
                row.danger_grade,
                row.threat_tier,
                bands[5],
                grade_positions,
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
# The authored bestiary rows (docs/lore/bestiary.md). Display/description prose
# is the authored zh-TW narrative; the published appearance excerpt is the same
# sentence's physical clause. Every value below is an authored literal
# transcribed as written, never re-derived, re-tuned, re-rounded, or
# interpolated from a display name, a description, a threat tier, another
# variant, or a tier band. MP and SP are the authored resource pools of the
# variants whose mechanic has landed and authored zeros for the rest;
# ``magic_power`` is zero for every variant and every tier's magic band is
# deliberately ``(0, 0)``.
#
# ``profile_required`` is authored per row and is ``True`` for every currently
# shipped row: each ships a complete profile and a danger grade, and the
# declaration keeps that completeness an obligation rather than an incidental fact
# about today's data. A future row authored without a profile states ``False``
# and keeps the tier-band fallback of individual construction.
#
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
        "牠們造成的麻煩集中於收穫期；田地照常耕作，反覆造訪的族群則會損耗尚未收起的穀物。"
        "牠們的氣流只震得動乾燥鬆脫的成熟穀粒，濕穀與牢固的未熟穗會留在穗上。"
        "這股氣流的力量集中在穗間，糧車與作物都保持原樣，影響範圍也只及於族群停留的一小片田地。"
        "近身時，牠會配合短促氣流啄擊，命中後使對手短暫分心；此招在任何地點都能使用，效果集中於被啄中的對手。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種在世界設定中沒有已定的起源真相；設計刻意不記載創造者、"
        "魔力污染或迷宮成因，任何此類說法都只是世界內未經證實的猜想。",
        "（作者私有：作者解釋）作為收穫期的低階麻煩來源，示範能力邊界如何限制風屬性生態而"
        "以近身啄擊與短暫命中干擾呈現微弱氣流，震穀生態仍不改造戰場；棲地相容性指向東部平原。",
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
        "大量聚集時，初次入港的小船可能誤判岸邊訊號；靠近礁洞的人也可能受到螯足攻擊。"
        "牠們重現的是附近既有光源的節奏，斑紋的明暗始終對應真實燈光，周圍物體也保持本來面貌。"
        "牠會在螯擊時收緊甲殼，短暫提高自身防禦；這項動作在有光或無光處都能使用。"
        "發光斑紋專門呼應燈光，螯擊則是單純的近身攻擊。",
        ("southeast_coast", "southwest_coast"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；發光斑紋的成因在設定中保持未記載。",
        "（作者私有：作者解釋）低階物種的第二個方向：追光生態保留既有光源條件；"
        "戰鬥採螯擊與甲殼防護，排除幻覺與治療。",
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
        "居民從環狀排列、異常牢固的小土埂辨認巢穴；這些土埂能撐過普通雨水，因此棄置巢穴也會留下痕跡。"
        "族群沿灌溉渠築巢時，土埂可能堵住分水口，坑洞則妨礙農具與牲畜通行。"
        "牠們的土屬性力量作用於巢穴周圍的鬆土，岩盤、城牆與石造基礎都保持完好。"
        "洞道是牠們逃離時一路奔跑穿過的通路。"
        "受逼近時，牠會以土屬性力量穩住身體後蹬擊，短暫提高自身防禦；此招在平地上隨時可用，效果只作用在牠自己身上。",
        ("eastern_plains", "western_hills_valleys"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；土屬性力量的來源不在設定中交代。",
        "（作者私有：作者解釋）以地形改造描述低階危害（分水口堵塞、通行妨礙），"
        "戰鬥以蹬擊與自身防禦呈現，不附帶定身、封路或瞬間移動。",
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
        "採石工人會留意牠們的敲岩聲，因為族群常出現在鬆動岩坡附近；"
        "牠們占據狹窄運料路線時，便會擋住整條運料線。"
        "脈動的作用範圍限於接觸處周圍的既有鬆石，完整岩盤與遠處地面都保持穩固。"
        "落石脈動需要接觸岩面及既有鬆石；近身角撞則在任何地面都能使用，"
        "命中後使對手短暫步伐不穩，傷害來自角撞本身。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；敲岩與脈動的來源不在設定中交代。",
        "（作者私有：作者解釋）中階物種示範地形依賴型能力：落石生態取決於既有鬆石，戰鬥角撞與短暫步伐干擾無環境條件，"
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
        "聚霧依賴既有霧氣，霧氣越濃，聚霧的掩護效果越好；近身時的鬃風佯撲在任何天候都能使用，命中後使對手短暫誤判動作，戰鬥中的威力取決於佯撲本身。"
        "牠始終留下足跡、氣味與聲音，獵人可以循著這些痕跡追蹤；牠的移動完全依靠自己的腳程，霧氣只改變獵物對牠來向的判斷。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；聚霧能力的來源不在設定中交代。",
        "（作者私有：作者解釋）以霧氣限定聚霧生態；近身佯撲及短暫命中干擾由鬃毛氣流與動作產生，作為中階獵食者的敘事邊界，"
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
        "牠在接觸活物時，透過水屬性力量吸取對方的部分魔力。"
        "施法者與牠纏鬥時，常先察覺魔力消耗異常，再意識到危險。"
        "牠依靠咬合與伏擊捕食，吸取發生在咬合接觸的瞬間；"
        "被吸走的是對方當下可用的魔力，休息後便會回復，"
        "吞潮鱷則把吸得的魔力納入自己的儲備。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；吸取魔力的成因不在設定中交代。",
        "（作者私有：作者解釋）以近身水屬性咬合吸取魔力作為資源消耗型危害，"
        "限制無遠程抽取、無生命治療與無永久魔力降低。",
        "（作者私有：尚未證實的猜想）渡運站傳說河口鱷群受沉沒魔法器物吸引，沒有實地證實。",
        "bank_lurker",
        True,
    ),
    MonsterSpecies(
        "mudfilm_slime",
        "泥膜史萊姆",
        "泥膜史萊姆棲息於潮濕溝岸、舊灌溉支渠與滲水洞口，以水膜中的腐葉碎屑及微小生物為食。"
        "透明膠體外膜黏集細泥，收縮時將泥粒壓成薄韌護膜；移動時，泥紋沿著體表摺疊。",
        "半透明膠體貼著濕地起伏，外膜浮著細緻泥紋。"
        "收膜時，泥粒聚成較深的環帶，撞擊留下的缺口隨著身體舒展露出濕亮膠質。",
        "牠通常獨自行動，濕潤處可見數隻分散覓食。靠近的腳步會使牠縮向陰濕處；"
        "遭到逼近時，牠收緊泥膜護住身體，再以短距離撞擊自衛。"
        "聚集的個體將細泥帶到狹窄分水口，農人會疏通渠口並處理反覆停留的個體。"
        "牠的活動集中於保有水膜的陰濕地帶，護膜則由體表已附著的細泥形成。",
        ("eastern_plains", "western_hills_valleys"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；泥膜的成因不在設定中交代。",
        "（作者私有：作者解釋）低階防禦型濕地物種：體表附著的細泥收縮成護膜，"
        "生態連結窄分水口的淤積；戰鬥呈現為自身護膜與接觸撞擊。棲地限於明確宣告的陰濕地塊。",
        "（作者私有：尚未證實的猜想）農人傳說泥膜史萊姆停留過的渠口特別清澈，這種說法尚未證實。",
        "mudbank_dweller",
        True,
    ),
    MonsterSpecies(
        "wax_pouch_rat",
        "蠟囊鼠",
        "蠟囊鼠是約家貓大小的鼠類，活動於平原田界、荒廢糧站與丘陵運糧道旁。"
        "牠的頰囊分泌薄蠟，把收集的穀粒裹成小團，藏在潮濕巢穴中。",
        "灰褐毛皮貼著圓身，鼓起的頰側帶著細亮蠟痕。"
        "腹側毛略顯光滑，長尾在鑽縫時貼向身後；巢邊常留著帶齒痕的蠟封穀團。",
        "小型家族共同覓食與搬運穀粒，蠟膜替巢中的穀團提供短期防潮。"
        "牠們也把少量蠟抹在腹側毛上，沿濕窄縫隙滑行。"
        "遇人時多半退避，藏糧巢口遭到封堵時便聚集自衛。"
        "待運穀物、破損糧袋與廢棄倉底提供覓食和築巢機會；"
        "妥善封存糧食、清理舊巢，能減少反覆接觸。近身時，牠靠咬擊與靈巧翻身應對威脅。",
        ("eastern_plains", "western_hills_valleys"),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；頰囊薄蠟的成因不在設定中交代。",
        "（作者私有：作者解釋）低階家族型鼠類：頰囊薄蠟為穀團短期防潮、"
        "腹側蠟層支持窄縫滑行，連結荒廢糧站與運糧道；戰鬥呈現為咬擊與自身短暫敏捷提升。",
        "（作者私有：尚未證實的猜想）糧站工人相信蠟封穀團能保存一整季，這種說法尚未證實。",
        "wax_cache_forager",
        True,
    ),
    MonsterSpecies(
        "sticky_palm_goblin",
        "膠掌小鬼",
        "膠掌小鬼是耳大、四肢細長、掌面寬的小鬼型魔獸，活動於丘陵灌木、廢棄採石地與岩棚下。"
        "掌部的短效黏液將枯枝、碎石及獸毛黏成懸掛巢，也協助牠攀附粗糙表面。",
        "瘦長身軀覆著淡綠色粗皮，寬掌與細長手指在攀爬時張開。"
        "指尖帶著黏亮痕跡，身旁的懸巢掛著細枝、繩絮與零碎石片。",
        "小群個體共同覓食、搬運巢材，以短促啼叫與敲擊傳遞警戒。"
        "牠們熟練運用手邊物件，能合作驅趕靠近巢穴的動物。"
        "人類工地留下的繩束、木片及保溫材料容易被搬進巢中；"
        "巢群占據通風口或岩棚通道時，工人會請人處理。"
        "黏液適合附著輕小巢材，雨水使膠膜逐漸稀薄。"
        "近身抓扯讓對手短暫失去動作節奏，覓食個體則傾向沿岩面退避。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；掌部黏液的成因不在設定中交代。",
        "（作者私有：作者解釋）低階社群型魔物：短效掌部黏液支撐懸掛巢、攀附與輕小巢材收集；"
        "溝通限於動物式啼叫、敲擊與學習而來的物件使用，與獸人族的登錄與描寫分開。"
        "戰鬥呈現為抓扯與命中後短暫的動作節奏干擾。",
        "（作者私有：尚未證實的猜想）採石工人說膠掌小鬼會模仿人類的敲擊節奏，這種說法尚未證實。",
        "hanging_nest_forager",
        True,
    ),
    MonsterSpecies(
        "ember_bristle_boar",
        "焙鬃野豬",
        "焙鬃野豬生活於西部偏遠岩林與廢棄燒炭地，會用肩背鬃毛的局部熱力烘乾泥窩、烘軟挖出的根莖。"
        "粗鬃末端在發熱時透出暗紅色，巢地留下乾燥土圈與烘焦根皮。",
        "厚實肩背披著粗硬鬃毛，短獠牙從寬吻兩側向外彎出。"
        "發熱時，鬃尖透出暗紅光；轉身時，乾燥根皮與土屑沿著背側抖落。",
        "牠通常獨居，長期使用少數泥窩與覓食路線，從根莖與林地食物取得日常養分。"
        "舊炭窯與背風岩坡提供乾燥住處，重複使用的運料道也可能成為領域的一部分。"
        "工人遇上占路個體時會改道，再委託熟練隊伍處理。"
        "牠以自身魔力維持鬃熱，配合身體力量作短程衝撞與近身甩鬃；熱力與動作都受自身資源支配。"
        "首隻指定個體因醒目的背鬃被稱為「赤背」。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鬃毛熱力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居野豬：以自身魔力維持肩背鬃毛的局部熱力，"
        "連結烘乾泥窩與烘軟根莖；戰鬥呈現為身體力量主導的火屬性物理衝撞與橫掃，"
        "魔力資質維持高階帶狀值。",
        "（作者私有：尚未證實的猜想）燒炭工人相信焙鬃野豬偏愛舊炭窯是為了取暖，這種說法尚未證實。",
        "warm_den_boar",
        True,
    ),
    MonsterSpecies(
        "spore_cap_mushroom",
        "孢傘菇",
        "孢傘菇是約幼犬大小的步行蕈類魔物，生活於北部深林的倒木、腐葉堆與巨木根間。"
        "牠以菌柄底部的短根緩慢挪動，從潮濕的腐木吸取養分。",
        "灰褐色的寬大菌傘覆著細密褶紋，傘緣垂著淡黃色孢粉。"
        "粗短菌柄底部分出數條短根，移動時在腐葉上留下細長拖痕。",
        "孢傘菇成群停留在同一段倒木上，菌傘受到碰撞或擠壓時，會噴出帶著微弱暗屬性的孢粉。"
        "吸入孢粉的動物會短暫視線昏沉，群落便趁這段時間挪回腐木深處。"
        "孢粉飄散範圍約一臂之遠；"
        "雨天時孢粉沾濕結團，噴出的量隨之減少。"
        "往返深林邊緣的採集者與巫醫會留意傘緣的黃粉，因為群落常占據他們採藥與拾柴的倒木。"
        "近身時，牠以菌傘頂撞對手，撞中後揚起孢粉，使對手短暫看不準目標。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；孢粉暗屬性的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蕈類：孢粉只在菌傘受撞擊或擠壓時散出，作用為短暫的視線昏沉，不造成中毒、睡眠或持續傷害；戰鬥呈現為頂撞與命中後的短暫命中下降。連結深林邊緣的採藥與拾柴。",
        "（作者私有：尚未證實的猜想）巫醫窟的藥師傳說菌環型站過的土壤能讓藥草長得更好，這種說法尚未證實。",
        "rotlog_sprout",
        True,
    ),
    MonsterSpecies(
        "moss_quill_porcupine",
        "苔棘豪豬",
        "苔棘豪豬是中型犬大小的豪豬類魔獸，生活於北部深林的林緣、倒木下的空洞與巨木根部的土穴。",
        "背上密生長棘，棘根長著一層濕綠苔蘚。"
        "圓鈍的頭部帶著短鬚，前爪粗短，啃過的樹皮上留著成排齒痕。",
        "牠通常獨居，夜間沿固定路線啃食樹皮、嫩根與蕈類，特別喜歡舔食帶有鹽分的東西。"
        "被汗水浸過的皮帶、鞍具與營地遺留的鹽漬食物，都會引牠靠近。"
        "遇到威脅時，牠以土屬性力量讓棘根周圍的苔土緊縮硬化，整排長棘隨之挺立，再轉身以背部倒撞過去；"
        "硬化維持片刻，作用在牠自己的棘根上。"
        "探險隊在林緣紮營時會把鞍具吊高，免得隔天早上發現皮帶被啃斷。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；棘根苔層硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居豪豬：土屬性力量只硬化自身棘根周圍的苔土，不射出棘刺、不造成中毒或持續傷害；戰鬥呈現為背部倒撞與自身短暫防禦提升。舔鹽習性連結林緣營地的鞍具損耗。",
        "（作者私有：尚未證實的猜想）北林堡的獵人說苔棘豪豬會記住給過鹽的人，這種說法尚未證實。",
        "quill_forager",
        True,
    ),
    MonsterSpecies(
        "hollow_tree_bat",
        "空木蝠",
        "空木蝠是翼展約一臂寬的蝙蝠類魔獸，成群棲息於北部深林巨木的中空樹幹與迷宮入口附近的岩縫。",
        "深褐色短毛覆蓋小巧身軀，薄翼膜在火光下透出暗紅血管。"
        "尖耳大而薄，口中兩枚細長門牙向前突出。",
        "黃昏時，群體從同一株空心巨木湧出，在林冠下穿梭捕食飛蟲。"
        "牠們以叫聲辨認方向，在不透光的樹洞與岩縫裡也能自在飛行。"
        "牠們會落在熟睡的鹿與馱獸身上，以帶著暗屬性的門牙咬開淺口，從咬口吸取少量血氣，轉為自身的生命；"
        "每次咬合吸取的分量有限，傷口隔日即可癒合。"
        "深入迷宮的探險隊常在入口附近遇上整群空木蝠，夜裡守營的人會替馱獸蓋上厚布。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；門牙暗屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蝙蝠：暗屬性門牙只在咬合命中時吸取少量生命，不傳染疾病、不造成持續失血或永久傷害；戰鬥呈現為咬擊與命中後的固定生命吸取。連結迷宮入口與探險隊的夜間營地。",
        "（作者私有：尚未證實的猜想）探險者之間流傳空木蝠群聚的樹洞附近必有迷宮入口，這種說法尚未證實。",
        "hollow_roost_flier",
        True,
    ),
    MonsterSpecies(
        "hush_wing_owl",
        "靜羽梟",
        "靜羽梟是雙翼展開近一人高的大型貓頭鷹類魔獸，獨自或成對棲息於北部深林巨木高處的樹洞。",
        "灰綠色羽毛帶著苔蘚般的斑紋，停在樹枝上時幾乎與樹皮融為一體。"
        "圓臉盤中央是一對琥珀色大眼，腳爪粗壯，趾尖彎鉤。",
        "牠在黃昏與深夜狩獵，以微弱風屬性力量梳開翼緣細羽，讓拍翼聲散進周圍的風裡，再貼著林冠滑向獵物。"
        "這股風力作用在牠自己的羽翼周圍，飛行與攻擊的方向由牠的腳爪與身形決定。"
        "牠捕食野兔、松鼠與落單的空木蝠，也會撲向夜裡在林間移動的小型馱獸。"
        "獵人在深林營地過夜時，會留意頭頂樹枝上的琥珀色眼光，並把燈火留在馱獸身旁。"
        "近身時，牠以腳爪掠擊對手，擊出後順勢藉風抬升，短暫變得更加靈活。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；靜羽風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居獵食者：風屬性只梳開自身翼緣細羽，使拍翼聲散開，不造成隱形、催眠或改變他人感官；戰鬥呈現為腳爪掠擊與自身短暫敏捷提升。黃昏與深夜才主動接觸。",
        "（作者私有：尚未證實的猜想）虎嘯城的獵人相信靜羽梟的叫聲預示天氣轉壞，這種說法尚未證實。",
        "hush_wing_hunter",
        True,
    ),
    MonsterSpecies(
        "vine_net_spider",
        "藤網蛛",
        "藤網蛛是身軀約有圓盾大小的蜘蛛類魔獸，獨自生活在北部深林藤蔓糾結的林下與獸徑兩側。",
        "暗綠色身軀覆著短硬毛，八條長腳的關節帶著樹皮般的褐色環紋。"
        "腹部末端的紡器旁常黏著剝下的藤皮纖維。",
        "牠會剝下藤蔓外皮，把纖維與自己吐出的絲撚在一起，織成能兜住小鹿的藤網，橫跨在獸徑兩側的樹幹之間。"
        "藤網的顏色與周圍藤蔓相同，晨露沾上時才顯出網形。"
        "牠守在網邊等待獵物，捕食鹿、野豬幼獸與誤闖的大型鳥類。"
        "藤網的韌度來自藤皮纖維，火焰與利刃都能切開它，探險隊在深林開路時會帶著砍刀與火把清出通道。"
        "近身時，牠以前腳擲出黏絲纏住對手的腿腳，命中後使對手短暫行動遲緩。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；藤皮纖維與絲線結合的成因不在設定中交代。",
        "（作者私有：作者解釋）中階伏擊型蜘蛛：絲線結合剝下的藤皮纖維形成藤網，戰鬥中的黏絲只在命中時短暫降低敏捷，不定身、不造成中毒或持續傷害。連結深林開路與獸徑狩獵。",
        "（作者私有：尚未證實的猜想）北林堡的工匠相信藤網蛛的舊網纖維能編出最耐用的弓弦，這種說法尚未證實。",
        "vine_weaver",
        True,
    ),
    MonsterSpecies(
        "moss_crown_stag",
        "苔冠巨鹿",
        "苔冠巨鹿是肩高約兩人的巨大鹿類魔獸，獨自漫遊於北部深林巨木之間的林間空地。",
        "寬闊的鹿角如枯枝般分岔，角上長滿苔蘚、蕨葉與垂落的細藤，遠看如同林間移動的一叢樹冠。"
        "灰褐色長毛垂到膝下，蹄子寬大，每一步都在腐葉上壓出深坑。",
        "牠以嫩枝、苔蘚與林間空地的草本植物為食，會把鹿角抵在巨木樹幹上磨擦，替角上的苔層換上新的藤葉。"
        "牠能以土屬性力量讓角上的苔層與藤根緊實硬化，使整副鹿角沉重如盤根。"
        "發情期間，牠會占據一片林間空地，把闖入的大型動物撞出空地。"
        "往返深林的探險隊會在遠處認出那叢移動的樹冠，提早改走另一條路；"
        "牠把空地選在探險隊的必經之處時，公會便會張貼討伐委託。"
        "牠以硬化的苔冠衝撞單一對手，也會甩動鹿角橫掃身旁的對手；"
        "衝撞與橫掃都耗費牠自身的魔力與體力。"
        "首隻指定個體因角上蒼綠的苔冠被稱為「蒼冠」。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鹿角苔層硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨鹿：土屬性力量只硬化自身鹿角上的苔層與藤根，不操縱植物、不改變地形，也不具神性或守護森林的使命；戰鬥呈現為土屬性物理衝撞與橫掃，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）虎嘯城的長老說苔冠巨鹿是深林最古老的居民，這種說法尚未證實。",
        "wood_crown_elder",
        True,
    ),
    MonsterSpecies(
        "mist_spring_frog",
        "霧泉蛙",
        "霧泉蛙是約手掌大小的蛙類魔獸，成群棲息於中央山脈山腰的滲水岩壁與霧中泉眼。",
        "灰藍色皮膚帶著細小水珠般的疣點，在霧裡泛著微光。"
        "後腿修長，指端長著吸盤，能貼在濕滑的岩壁上；"
        "喉囊鼓起時呈半透明的淡青色。",
        "牠們白天貼在泉眼周圍的岩壁上，以皮膚吸取霧氣中的水分，傍晚才成群鳴叫、捕食飛蟲。"
        "牠的舌尖帶著微弱水屬性力量，黏中獵物或對手時，會從對方身上汲走少量魔力，轉為自身的魔力；"
        "每次汲取的分量有限，被汲走的魔力會隨休息逐步恢復。"
        "翻越山徑的旅人與上山採藥的人都在這些泉眼補水，泉邊一旦擠滿霧泉蛙，取水的人就得先把蛙群趕開。"
        "近身時，牠彈出長舌拍打對手，舌尖黏中時順勢汲取魔力。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；舌尖水屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蛙類：水屬性舌尖只在命中時汲取少量魔力，不造成中毒、麻痺或持續傷害；戰鬥呈現為舌擊與命中後的固定魔力汲取。連結山徑泉眼的取水。",
        "（作者私有：尚未證實的猜想）斷崖鎮的採藥人說霧泉蛙鳴叫得越早，當晚的霧就越濃，這種說法尚未證實。",
        "seep_sipper",
        True,
    ),
    MonsterSpecies(
        "warm_rock_salamander",
        "暖岩蠑螈",
        "暖岩蠑螈是約前臂長的蠑螈類魔獸，獨自棲息於中央山脈向陽的岩縫與碎石坡。",
        "黑褐色濕潤皮膚上散布著橙紅斑點，體溫升高時斑點會隱約透出火光。"
        "頭部扁平，四肢短小，尾巴約與身體等長。",
        "山上冷霧終日不散，牠卻能以微弱火屬性力量讓自己的皮膚發熱，在其他小動物凍得遲緩的清晨照樣爬出岩縫捕食甲蟲與小蛇。"
        "這股熱力停留在牠自己的皮膚上，發熱越久越耗體力，所以牠大半時間趴在向陽的岩面上曬太陽。"
        "山徑旁的避難石屋留有火塘，夜裡餘溫不散，暖岩蠑螈常鑽進火塘邊的石縫過夜；"
        "旅人伸手撿柴時被咬，是石屋裡常聽到的小意外。"
        "近身時，牠咬住對手，同時讓斑點驟然發亮，短時間內咬勁更強。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；皮膚火屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居蠑螈：火屬性只讓自身皮膚發熱，不點燃周圍物品、不噴火、不造成燒傷狀態；戰鬥呈現為咬擊與自身短暫攻擊提升（燃身換爆發）。連結山徑避難石屋的火塘。",
        "（作者私有：尚未證實的猜想）銀嶺鎮的礦工相信石屋火塘裡有暖岩蠑螈過夜，代表那座石屋整晚都會溫暖，這種說法尚未證實。",
        "ledge_basker",
        True,
    ),
    MonsterSpecies(
        "bone_breaker_vulture",
        "碎骨鷲",
        "碎骨鷲是雙翼展開近兩人寬的大型鷲類魔獸，成對棲息於中央山脈雲霧上方的斷崖岩棚。",
        "頭頸覆著淡黃羽毛，眼周一圈紅色，嘴基垂著一撮黑色鬚羽。"
        "背羽灰黑，翼尖細長，飛行時翅膀幾乎一動也不動。",
        "牠以動物骨骼為主食，會叼起獸骨飛到高處，丟在固定的岩板上摔碎，再吞下骨片與骨髓。"
        "牠能以微弱風屬性力量讓翼下的冷風聚攏，在雲霧上方的上升氣流裡長時間懸停；"
        "這股風力作用在牠自己的翅膀周圍。"
        "每對碎骨鷲都有一塊用了多年的摔骨岩板，岩板四周鋪滿白色碎骨，牠會撲向靠近岩板的身影。"
        "斷崖鎮的採藥人上山採崖苔時，會繞開這些鋪滿碎骨的岩棚。"
        "近身時，牠俯衝撲擊對手，撲中後振翅掀起碎石與雪粒，使對手短暫看不準目標。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階成對棲息的鷲類：風屬性只聚攏自身翼下的氣流以懸停，不操控天氣或他人的移動；戰鬥呈現為俯衝撲擊與命中後短暫命中下降。連結採藥人的崖苔採集路線。",
        "（作者私有：尚未證實的猜想）斷崖鎮的老採藥人說摔骨岩板附近的崖苔長得最好，這種說法尚未證實。",
        "updraft_glider",
        True,
    ),
    MonsterSpecies(
        "mist_lamp_moth",
        "霧燈蛾",
        "霧燈蛾是雙翅展開約兩臂寬的大型蛾類魔獸，獨自棲息於中央山脈終年雲霧繚繞的山腰林帶。",
        "灰白翅膀上帶著兩枚暗色眼紋，翅緣垂著絨毛般的長鱗。"
        "羽狀觸角寬如手掌，身軀覆著厚密白毛，停在樹幹上時像一片積著霜的樹皮。",
        "牠白天收翅貼在霧中的樹幹上，入夜後循著光亮飛行，以花蜜與樹液為食。"
        "山徑上的避難石屋在霧夜會點燈指路，燈火常引來霧燈蛾繞著燈籠撲飛，翅膀撞得燈罩搖晃。"
        "牠的翅鱗帶著微弱暗屬性力量，鱗粉落在身上時會讓手腳短暫發沉；"
        "撲翅擊中對手的那一下，鱗粉才會大量抖落。"
        "守燈的人會在燈罩外加一層細網，讓燈光照得到山徑，蛾翅則碰不到燈火。"
        "近身時，牠以厚重的翅膀撲打對手，撲中時抖落鱗粉，使對手動作短暫遲緩。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翅鱗暗屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居蛾類：暗屬性翅鱗只在撲擊命中時抖落，作用為短暫手腳發沉，不造成中毒、睡眠、幻覺或持續傷害；戰鬥呈現為翅膀撲打與命中後短暫敏捷下降。連結山徑石屋的霧夜燈火。",
        "（作者私有：尚未證實的猜想）翻越山徑的旅人之間流傳，霧燈蛾繞燈越久，隔天的霧散得越快，這種說法尚未證實。",
        "lamp_seeker",
        True,
    ),
    MonsterSpecies(
        "rime_scale_serpent",
        "霜鱗巨蟒",
        "霜鱗巨蟒是身長超過十人並列的巨大蟒類魔獸，獨自盤踞於中央山脈霧氣積聚的深谷。",
        "灰白鱗片邊緣結著一層細霜，在霧中幾乎與覆雪的岩石融為一體。"
        "頭部寬如門板，琥珀色豎瞳，腹側鱗片隨呼吸起伏時會抖落細碎冰屑。",
        "牠以野山羊、碎骨鷲與誤入深谷的大型動物為食，一次飽食後能在谷底盤臥一整個月。"
        "牠能以冰屬性力量讓自己的鱗片結霜，盤在霧中時看起來像一段覆著霜雪的岩脊；"
        "結霜作用在牠自己的鱗片上。"
        "牠盤踞的深谷四周少有人跡，只有銀嶺鎮的探礦隊偶爾沿谷壁尋找銀脈。"
        "牠以結霜的獠牙噬咬單一對手，也會甩動長尾橫掃身旁的對手；"
        "噬咬與橫掃都耗費牠自身的魔力與體力。"
        "首隻指定個體因盤成一圈時像谷底的一道白霜環，被稱為「霜環」。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鱗片結霜的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨蟒：冰屬性只讓自身鱗片結霜，不凍結他人、不改變天氣，也不具神性或守護山脈的使命，與寒風中的歌聲無關；戰鬥呈現為冰屬性物理噬咬與橫掃，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）銀嶺鎮的老礦工說霜鱗巨蟒盤踞的深谷必定藏著銀脈，這種說法尚未證實。",
        "white_rime_coil",
        True,
    ),
    MonsterSpecies(
        "drum_wing_grouse",
        "鼓翼松雞",
        "鼓翼松雞是約小型犬大小的松雞類魔獸，成群生活於西北高地針葉林的林床與林間空地。",
        "雄雞羽毛黑藍，眼上一道紅色肉冠，尾羽展開時像一面半圓扇；"
        "雌雞羽色棕褐帶細斑，伏在林床上時與落針融成一片。",
        "牠們在林床上啄食松針、嫩芽與漿果，受驚時以微弱風屬性力量讓翼下的氣流驟然鼓起，從腳邊轟然驚飛，再貼著樹幹急轉閃避；"
        "這股風力作用在牠們自己的翅膀周圍。"
        "每年春天，雄雞聚在固定的林間空地上展尾鳴叫、互相爭鬥，這些求偶場也是獸人部族世代相傳的春季獵場，年輕獵人會在這裡練習追蹤與埋伏。"
        "求偶季的雄雞會撲向走進求偶場的任何身影，連牧人的山羊與獵人的獵犬也照撲不誤。"
        "近身時，牠鼓翼撲擊對手，撲出後順勢驚飛，短暫變得更加靈活。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居松雞：風屬性只鼓起自身翼下氣流以驚飛閃避，不造成擊退或改變他人移動；戰鬥呈現為鼓翼撲擊與自身短暫敏捷提升。連結獸人部族的春季獵場與年輕獵人的練習。",
        "（作者私有：尚未證實的猜想）獵鷹鎮的獵人說領場型雄雞鳴叫的那天早上，整片林子的獵物都會變得警覺，這種說法尚未證實。",
        "pine_floor_grouse",
        True,
    ),
    MonsterSpecies(
        "mud_dam_beaver",
        "泥壩河狸",
        "泥壩河狸是約中型犬大小的河狸類魔獸，以家族為單位生活於西北高地的溪流與渡口上游。",
        "濃密的深褐毛皮上常糊著一層乾泥，尾巴寬扁如槳，覆著鱗狀硬皮。"
        "門牙橘黃粗大，啃斷手臂粗的松樹只需片刻。",
        "牠們啃倒溪邊的樹木，以樹枝與溪泥築起橫跨溪流的水壩，再在壩後的水塘裡建造圓頂巢屋。"
        "牠們能以微弱土屬性力量讓糊上的溪泥迅速緊實，水壩因此撐得過春季融雪的大水，糊在自己毛皮上的泥層也會變得堅硬。"
        "西北高地的渡口聚落依靠穩定的溪水擺渡，河狸家族在上游築壩時，下游渡口的水位便忽高忽低，渡船的木樁也常被啃斷。"
        "近身時，牠以寬尾拍擊對手，拍擊時讓毛皮上的泥層緊實硬化，更耐得住反擊。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；溪泥緊實之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階家族群居河狸：土屬性力量只讓自身毛皮泥層與水壩溪泥緊實，不改變河道或操控水流；戰鬥呈現為尾擊與自身短暫防禦提升。連結渡口聚落的水位與渡船木樁。",
        "（作者私有：尚未證實的猜想）松濤渡的船夫相信老壩型築的水壩能預告當年融雪的早晚，這種說法尚未證實。",
        "dam_builder",
        True,
    ),
    MonsterSpecies(
        "ore_vein_mole",
        "礦脈鼴",
        "礦脈鼴是約貓大小的鼴類魔獸，獨自生活於西北高地礦脈裸露的岩壁下與林間空地的鬆土中。",
        "黑灰色短絨毛摸起來像天鵝絨，沾著閃亮的礦砂。"
        "前肢寬大如鏟，指爪粗厚，眼睛細小得藏在毛裡，粉紅色的鼻尖靈活地四處嗅探。",
        "牠沿著礦脈下方的鬆土挖掘長隧道，捕食土中的甲蟲幼蟲與蚯蚓，挖出的土堆在地面排成一列。"
        "牠能以微弱土屬性力量讓爪前的土石鬆動，挖起碎石層也很快；"
        "這股力量作用在牠爪前方一小片地面上。"
        "獸人部族在礦脈露頭處開採礦石，礦脈鼴的隧道常挖到採礦溝底下，溝壁因此坍落。"
        "近身時，牠以前爪刨擊對手，刨中時揚起一把礦砂打在對手臉上，使對手短暫看不準目標。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；爪前土石鬆動之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居鼴類：土屬性力量只鬆動爪前一小片土石，不造成地陷、崩塌或大範圍地形改變；戰鬥呈現為爪刨與命中後短暫命中下降。連結獸人部族的露頭採礦。",
        "（作者私有：尚未證實的猜想）鐵爪城的礦工說礦脈鼴挖出的土堆排成的那條線，就是礦脈延伸的方向，這種說法尚未證實。",
        "vein_digger",
        True,
    ),
    MonsterSpecies(
        "cache_raider_wolverine",
        "掠藏獾",
        "掠藏獾是體型比一般獾大上一倍、身軀粗壯的獾類魔獸，獨自遊走於西北高地針葉林與高地雪原之間的廣大範圍。",
        "深棕色長毛在兩側各有一道淡黃寬紋，從肩頭延伸到尾根。"
        "四肢短而粗，腳掌寬大，爪子彎長，頭部寬短，顎部肌肉鼓起如拳。",
        "牠一天能走過好幾座山頭，循著氣味找出埋在雪下的獸屍與其他動物藏起的食物。"
        "牠的顎部帶著異常的咬合力，咬得開凍硬的獸骨，也扳得開鐵製獸夾。"
        "獸人部族在季節性獵場佈下綿長的陷阱線，掠藏獾記得每一條走過的陷阱線，會沿線吃掉夾到的獵物，再把剩下的拖去藏起來。"
        "獵人巡陷阱時若發現獸夾被扳開、獵物只剩一撮毛，就知道牠來過。"
        "近身時，牠撲上去以顎部鉗住對手的手腳猛力扳扭，咬中時讓對手的護身架勢短暫鬆開。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；異常咬合力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居掠食者：異常咬合力屬於身體能力，不帶元素、不造成骨折或持續傷害；戰鬥呈現為鉗顎咬擊與命中後短暫防禦下降。命名與外觀刻意避開狼與熊，避免與獸人亞種混淆。連結獸人部族季節性獵場的陷阱線。",
        "（作者私有：尚未證實的猜想）霜風鎮的獵人說掠藏獾會故意避開設過兩次的陷阱，這種說法尚未證實。",
        "trapline_raider",
        True,
    ),
    MonsterSpecies(
        "ore_nest_griffin",
        "礦巢獅鷲",
        "礦巢獅鷲是雙翼展開超過四人寬的巨大有翼魔獸，生著鷹首與四足獸身，成對棲息於西北高地礦脈裸露的高崖。",
        "金褐色的鷹首帶著彎鉤巨喙，頸羽向下逐漸轉為覆蓋獸身的黃褐短毛。"
        "前足是鷹爪，後足是粗壯的四足獸腿，長尾末端垂著一簇深色毛。",
        "牠在高崖上以枯枝築成寬大的巢，巢裡鋪滿從礦脈岩壁上啄下的閃亮礦石碎片。"
        "牠以林間空地上的大型獸群為獵物，從高空盤旋鎖定落單的個體後俯衝而下。"
        "牠能以風屬性力量把氣流聚到翼下，讓沉重的身軀從崖頂起飛、在空中驟然轉向；"
        "這股風力作用在牠自己的雙翼周圍。"
        "獸人部族的老獵人與礦工都認得那些崖頂閃著礦光的巢，開採礦脈時會避開巢崖下方。"
        "牠以鷹爪俯衝擊打單一對手，也會在低空猛振雙翼，以翼下風壓撞向身旁所有對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體因頸羽在陽光下閃著金光，被稱為「金翎」。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階成對棲息的有翼魔獸：風屬性只把氣流聚到自身翼下以起飛與轉向，不操控天氣、不造成擊退或持續傷害，也不具神性、守護寶物的使命或精靈關聯；收集礦石碎片是築巢習性。外觀以鷹首與四足獸身描寫，不寫成貓科或獸人。戰鬥呈現為風屬性物理俯衝與範圍翼壓，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）鐵爪城的礦工相信礦巢獅鷲叼回巢裡的礦石碎片都來自最純的礦脈，這種說法尚未證實。",
        "windcrest_elder",
        True,
    ),
    MonsterSpecies(
        "clod_ball_beetle",
        "滾土甲蟲",
        "滾土甲蟲是約拳頭大小的甲蟲類魔獸，成對生活於東部大平原的牧場、官道與田埂一帶。",
        "黑亮的甲殼泛著深綠光澤，頭部前端長著一片鏟狀寬板。"
        "前腳扁平帶齒，適合推土與挖掘；"
        "後腳細長，能倒退著推動比自己大上數倍的土球。",
        "牠們把牧場的牛糞與田土揉成圓球，倒退著推回地洞，在土球裡產卵育幼。"
        "牠能以微弱土屬性力量讓揉好的土球迅速壓實，壓實後的土球硬如石塊，推過碎石路也不會散開。"
        "東部的官道兩側是牧場與田地，滾土甲蟲常把土球推上路面，牛車輪子壓到硬球就會顛簸卡住；"
        "牠們埋在田邊的土球，也會堵住灌溉渠的小水門。"
        "近身時，牠低頭以鏟狀頭板頂撞對手，同時把土球滾向對手腳邊，撞中時讓對手腳步一絆、短暫慢下來。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；壓實土球之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階成對生活的甲蟲：土屬性力量只讓自己揉成的土球壓實，不改變地形、不造成陷落；戰鬥呈現為頭板頂撞與命中後短暫敏捷下降（土讓腳下變壞）。連結官道牛車與灌溉渠水門。",
        "（作者私有：尚未證實的猜想）東牧鎮的牧人說滾土甲蟲把土球推往哪個方向，隔天的風就往哪裡吹，這種說法尚未證實。",
        "road_ball_roller",
        True,
    ),
    MonsterSpecies(
        "dust_mane_horse",
        "揚塵野馬",
        "揚塵野馬是肩高與人相當的野馬類魔獸，成小群奔馳於東部大平原的丘陵牧野與開闊草原。",
        "沙褐色的短毛沾滿塵土，鬃毛與尾毛又長又粗，奔跑時在身後拖出一道灰黃。"
        "四肢修長，蹄子寬大堅硬，蹄緣一圈顏色較深。",
        "牠們以三五匹為一群，清晨與黃昏在草原上吃草，白天躲在丘陵背風處休息。"
        "牠能以微弱風屬性力量讓氣流聚在四蹄周圍，起跑時一蹬就衝到全速，在草原上急轉也不會失足；"
        "這股風力繞在牠自己的蹄邊，跑得越久越耗體力。"
        "駿原鎮與東牧鎮靠養馬與放牧維生，野馬群常撞開牧場的木柵欄，啃光留給家畜的冬季草場，有時還把牧場的母馬引進野馬群裡。"
        "近身時，牠人立而起以前蹄踢擊對手，踢擊時蹄邊捲起一陣風，短時間內腳步更快。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；蹄邊風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階小群生活的野馬：風屬性只把氣流聚在自身四蹄周圍以加速與轉向，不颳起風暴、不推動他人；戰鬥呈現為前蹄踢擊與自身短暫敏捷提升。描寫維持動物體態，不與任何獸人亞種相比。連結駿原鎮的馬匹繁育與東牧鎮的牧場柵欄。",
        "（作者私有：尚未證實的猜想）駿原鎮的馴馬師相信跟過野馬群一季的母馬，生下的小馬跑得特別快，這種說法尚未證實。",
        "plain_runner",
        True,
    ),
    MonsterSpecies(
        "sluice_spear_heron",
        "渠矛蒼鷺",
        "渠矛蒼鷺是站起來與人齊高的鷺類魔獸，獨自涉行於東部大平原的灌溉渠、水門與魚塘邊。",
        "背羽灰藍，頸部細長雪白，頭頂後方垂著兩根黑色飾羽。"
        "暗黃色的長喙尖直如矛，雙腿細長，能在及膝的渠水裡一動也不動地站上半天。",
        "牠縮著長頸站在水門下方的急流邊，等魚群與青蛙游近。"
        "牠的頸部帶著異常的彈力，收縮的長頸能在眨眼間彈直，長喙刺進水裡的速度快得看不清。"
        "平原上的灌溉渠沿線都有農家挖的魚塘，渠矛蒼鷺會守在同一座水門旁，把一整池魚苗啄個精光；"
        "管水門的人走近時，牠也會揚喙刺向來人。"
        "近身時，牠以長喙疾刺對手，刺中時順勢甩起一片水花撲在對手臉上，讓對手短暫看不準目標。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；頸部異常彈力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居涉禽：頸部彈力屬於身體能力，不帶元素、不造成失明或持續傷害；戰鬥呈現為長喙疾刺與命中後短暫命中下降（水花撲面）。連結灌溉渠水門與農家魚塘。",
        "（作者私有：尚未證實的猜想）翠湖鎮的漁人說渠矛蒼鷺站在哪座水門下，那年那條渠的魚就最多，這種說法尚未證實。",
        "sluice_wader",
        True,
    ),
    MonsterSpecies(
        "lake_mound_turtle",
        "湖丘巨龜",
        "湖丘巨龜是背甲寬過一座小屋的巨大龜類魔獸，獨自棲息於東部大平原東北的湖沼深處。",
        "背甲上糊著一層厚實的湖泥，長滿蘆葦與水草，露出水面時看起來是一座小土丘。"
        "頭部粗大，鉤狀上顎的邊緣厚鈍如石，四肢粗短，覆著灰黑色的硬鱗。",
        "牠一年裡大半時間靜臥在湖底，以路過的大魚與水鳥為食。"
        "牠能以土屬性力量讓背甲上的湖泥結得緊實，泥層一年比一年厚，上頭的蘆葦也越長越高。"
        "沉鐘鎮與周邊湖畔的漁人熟悉湖上每一座蘆葦小丘，下網時會避開會移動的那一座。"
        "牠以巨顎咬住單一對手，也會撐起身軀把背甲猛力砸向地面，讓身旁的泥地一陣翻湧，撞向四周所有對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體的背甲上長著一叢秋天開白花的蘆葦，被稱為「白蘆」。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；背甲泥層緊實之力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨龜：土屬性只讓自身背甲上的湖泥緊實，並在砸地時讓身旁泥地翻湧，不引發地震、不改變湖岸地形；戰鬥呈現為土屬性物理咬擊與範圍震地，資源耗盡後回到普通攻擊。不具神性、守護使命或精靈關聯。連結沉鐘鎮湖畔漁人的下網習慣。",
        "（作者私有：尚未證實的猜想）沉鐘鎮的老漁人說湖丘巨龜背上的蘆葦開花的那年，湖裡的魚會特別多，這種說法尚未證實。",
        "wide_mound_elder",
        True,
    ),
    MonsterSpecies(
        "flat_leap_goby",
        "灘跳魚",
        "灘跳魚是約小臂長的鰕虎類魔獸，成群生活於東南海岸河口的潮間泥灘與鹽沼。",
        "灰褐色的身體布滿藍色亮點，一對大眼長在頭頂，能各自轉動。"
        "胸鰭粗壯，撐在泥上時形如一對短腿；"
        "背鰭展開時是一面帶黑邊的小旗。",
        "退潮後，牠們撐著胸鰭在泥灘上爬行，啃食泥面的藻類與小蟹。"
        "牠的胸鰭與尾巴帶著異常的力氣，胸鰭一撐、尾巴一甩就能躍過一人高的距離，在泥灘上比人走得還快。"
        "金穗港與東灣港的河口泥灘是漁家挖蛤、晾網的地方，灘跳魚群會把挖好的蛤坑占成自己的洞口，遇到有人靠近便成群跳起。"
        "近身時，牠撲上前以尾巴拍擊對手，拍中時甩起一團濕泥糊在對手臉上，讓對手短暫看不準目標。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；胸鰭與尾巴異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居鰕虎：胸鰭與尾巴的力氣屬於身體能力，不帶元素、不造成中毒或持續傷害；戰鬥呈現為尾擊與命中後短暫命中下降（濺泥）。連結河口漁家的挖蛤與晾網。",
        "（作者私有：尚未證實的猜想）東灣港的挖蛤人說灘跳魚的泥塔築得越高，下個月的大潮就越大，這種說法尚未證實。",
        "mudflat_skipper",
        True,
    ),
    MonsterSpecies(
        "mast_wind_gull",
        "桅風海鷗",
        "桅風海鷗是雙翼展開約一臂半寬的鷗類魔獸，成群棲息於東南海岸的港口、碼頭與防波堤。",
        "頭胸雪白，背羽淺灰，翼尖一截墨黑。"
        "黃色的嘴粗壯帶鉤，下嘴尖有一點紅斑，雙腳是橘黃色的蹼足。",
        "牠們在桅杆之間盤旋，盯著魚市攤上的漁獲與碼頭工人手裡的乾糧。"
        "牠能以微弱風屬性力量在翼下聚起一股側風，從盤旋中驟然橫掠而下，叼走攤上的魚後一個轉身飛回桅頂；"
        "這股風力在牠自己的雙翼下聚起，連續掠飛幾次就得停下來喘氣。"
        "金穗港的魚市每天清晨開市，攤販得一手收錢、一手揮竿趕鷗，貨箱上的魚乾也常被整串叼走。"
        "近身時，牠俯身啄擊對手，啄擊時翼下的側風一聚，短時間內身形更輕快。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下側風的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居海鷗：風屬性只在自身翼下聚起側風以橫掠與轉身，不颳起海風、不影響船帆；戰鬥呈現為啄擊與自身短暫敏捷提升。連結金穗港魚市與碼頭貨箱。",
        "（作者私有：尚未證實的猜想）南岬港的船員相信桅風海鷗聚在哪艘船的桅頂，那艘船下一趟就會滿載，這種說法尚未證實。",
        "mast_circler",
        True,
    ),
    MonsterSpecies(
        "breakwater_seal",
        "臥堤海豹",
        "臥堤海豹是體長超過一人的海豹類魔獸，成群棲息於東南海岸的防波堤、礁岩與河口沙洲。",
        "灰色短毛上散布著深色斑點，身軀圓滾，頭部渾圓，嘴邊一圈硬鬚。"
        "四肢化成鰭狀，後鰭向後並攏，上岸時以腹部貼地蠕行。",
        "牠們漲潮時下海捕魚，退潮後成群爬上防波堤與礁岩曬太陽。"
        "牠的腹毛帶著異常的滑油，在濕滑的石面上一挺身就能滑出好幾丈，比在沙地上爬行快得多。"
        "東南海岸的漁船靠防波堤內側停泊，臥堤海豹群會占滿堤上的繫船石與曬網架，扯破攤開的漁網，搶食網中漁獲。"
        "近身時，牠挺身沿著濕地滑向對手，以整個身軀壓撞過去，撞中時讓對手在濕滑的地面上失去重心，短時間內腳步遲緩。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；腹毛滑油的成因不在設定中交代。",
        "（作者私有：作者解釋）中階群居海豹：腹毛滑油屬於身體能力，不帶元素、不讓地面結冰或持續濕滑；戰鬥呈現為滑行壓撞與命中後短暫敏捷下降。描寫維持海豹體態，不與任何獸人亞種相比。連結漁船停泊的防波堤與曬網架。",
        "（作者私有：尚未證實的猜想）金穗港的老船夫說臥堤海豹全群提早下海的日子，午後必有大浪，這種說法尚未證實。",
        "pier_basker",
        True,
    ),
    MonsterSpecies(
        "salt_column_ant",
        "負鹽蟻",
        "負鹽蟻是約手掌長的蟻類魔獸，成群生活於西南海岸的鹽道、曬鹽場堤岸與橄欖林的乾地。",
        "赤褐色的身體分成頭、胸、腹三節，表面光滑發亮。"
        "頭部方大，一對鉗狀大顎的邊緣帶著細齒；"
        "六條腿細長，觸角在頭前不停擺動。",
        "牠們在乾燥的土坡下挖出深巢，排成長列外出覓食，專找鹽粒、橄欖與掉落的乾果。"
        "牠的大顎與頸部帶著異常的力氣，一隻就能銜起比自己重上好幾倍的鹽塊，拖著倒退回巢；"
        "巢口的土丘因此結著一層白鹽殼。"
        "鹽道城往海邊的鹽道上，運鹽的驢車常被蟻列攔住，麻袋被咬開，鹽粒一路漏進蟻巢。"
        "近身時，牠以大顎咬住對手的腳踝向後拖拽，咬中時讓對手腳下一沉，短時間內步伐遲緩。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；大顎異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居螞蟻：大顎的力氣屬於身體能力，不帶元素、不噴酸、不造成中毒；戰鬥呈現為咬住拖拽與命中後短暫敏捷下降。描寫維持昆蟲體態。連結鹽道城的運鹽驢車與巢口鹽殼。",
        "（作者私有：尚未證實的猜想）鹽道城的趕驢人說負鹽蟻把巢口的鹽殼加厚的那年，雨季會來得特別晚，這種說法尚未證實。",
        "salt_hauler",
        True,
    ),
    MonsterSpecies(
        "stiff_arm_starfish",
        "硬腕海星",
        "硬腕海星是五條腕足張開約一臂寬的海星類魔獸，成片棲息於西南海岸的潮池、蚵架與造船坊的下水滑道。",
        "身體是五條粗短腕足連成的星形，背面橙紅，布滿顆粒狀的硬疣；"
        "每條腕足的腹面排著兩列細密的管足。",
        "牠們以管足沿著礁石與蚵架爬行，用腕足扳開蚵殼與貽貝，吃裡頭的肉。"
        "牠的體壁帶著異常的變化力，平時柔軟，一受驚就在眨眼間硬得像石頭，緊貼在礁石上承受整道浪頭。"
        "漁灣鎮與南潮港的漁家在潮間帶搭起蚵架，硬腕海星成片爬上架子，一夜就能吃空一整排蚵殼；"
        "造船坊的下水滑道也常被牠們占住，木船滑下時刮傷船底。"
        "近身時，牠撐起腕足撲壓到對手身上，撲壓時全身體壁一併硬化，短時間內更加堅固。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；體壁瞬間硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群聚海星：體壁硬化屬於身體能力，不帶元素、不讓周圍環境變硬；戰鬥呈現為腕足撲壓與自身短暫防禦提升。連結漁家蚵架與造船坊的下水滑道。",
        "（作者私有：尚未證實的猜想）漁灣鎮的老漁婦說硬腕海星背上的硬疣越紅，當年的蚵就越肥，這種說法尚未證實。",
        "oyster_rack_creeper",
        True,
    ),
    MonsterSpecies(
        "shell_crack_shrimp",
        "碎殼蝦",
        "碎殼蝦是體長約有半個人高的螳螂蝦類魔獸，獨自穴居於西南海岸港灣的淺灘、礁縫與石砌海堤。",
        "甲殼泛著綠、紅、藍交錯的光澤，一對長在短柄上的眼睛各自轉動。"
        "胸前收著一對錘狀的捕肢，平時折疊貼在身下，末端圓鈍堅硬，形如兩柄小錘。",
        "牠在淺灘的沙底與海堤的石縫裡挖出洞穴，守在洞口等待路過的蟹與貝。"
        "牠的錘狀捕肢帶著異常的爆發力，彈出時快得看不清，一擊就能敲碎蟹殼與厚實的蚵殼。"
        "西南海岸的小港靠著精工器物的買賣維生，碼頭上常堆著待裝船的上釉陶罐與玻璃浮球；"
        "碎殼蝦把洞挖在碼頭石階下，夜裡出洞時會把擋路的陶罐敲出裂痕。"
        "近身時，牠彈出錘狀捕肢重擊對手，擊中時震裂對手的護具表面，短時間內防禦下降。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；錘狀捕肢爆發力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居螳螂蝦：捕肢的爆發力屬於身體能力，不帶元素、不發出衝擊波或雷光；戰鬥呈現為重擊與命中後短暫防禦下降。描寫維持甲殼類體態。連結港口碼頭待裝船的陶罐與玻璃浮球。",
        "（作者私有：尚未證實的猜想）南潮港的陶器商說聽得見碎殼蝦在石階下敲殼的夜晚，隔天的海面必定平靜，這種說法尚未證實。",
        "reef_burrow_striker",
        True,
    ),
    MonsterSpecies(
        "salt_snort_iguana",
        "噴鹽鬣蜥",
        "噴鹽鬣蜥是體長超過一人的鬣蜥類魔獸，成群棲息於西南海岸的黑色海崖與崖下的曬鹽場。",
        "深灰近黑的鱗皮粗糙如岩，背脊上一排尖刺從頸後延伸到尾根。"
        "頭部短而鈍圓，鼻孔周圍與頭頂結著一層白色鹽殼，四肢粗壯，爪子彎長。",
        "牠們白天成群趴在被太陽曬暖的崖石上，退潮時潛到崖腳啃食礁石上的海藻。"
        "牠鼻內的鹽腺帶著異常的力氣，能把吃進的海鹽濃成鹽水，猛力從鼻孔噴出，頭頂因此結著一層厚實的白鹽殼。"
        "海崖下的曬鹽場以石堤圍出成排的鹽田，堤面被太陽曬得溫熱，噴鹽鬣蜥常整群爬上堤面曬太陽，壓碎剛結好的鹽層，也把漁村攤在礁石上晾曬的海藻吃個精光。"
        "近身時，牠以鈍圓的頭頂撞對手，撞中時從鼻孔噴出一股濃鹽水，刺得對手短時間內看不準目標。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鼻內鹽腺異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）中階群居鬣蜥：鹽腺噴鹽屬於身體能力，不帶元素、不造成中毒或持續傷害；戰鬥呈現為頂撞與命中後短暫命中下降。描寫維持蜥蜴體態，不與鱷魚或蠑螈混同。連結海崖下的曬鹽場鹽田與漁村晾曬的海藻。",
        "（作者私有：尚未證實的猜想）曬鹽場的鹽工說噴鹽鬣蜥一整天都留在崖上的日子，隔天必定下雨，這種說法尚未證實。",
        "seacliff_basker",
        True,
    ),
    MonsterSpecies(
        "wreck_arm_octopus",
        "沉船巨蛸",
        "沉船巨蛸是八條觸腕張開能蓋住一艘漁船的巨大章魚類魔獸，獨自棲息於西南海岸海崖下的海蝕洞與擱淺的沉船殘骸。",
        "軟滑的身體泛著暗紅與褐色的斑紋，一對金黃的眼睛長在頭側，瞳孔是一道橫縫。"
        "八條觸腕粗如船纜，內側排滿兩列碗口大的吸盤，腕根之間藏著一張鉤狀的硬喙。",
        "牠白天縮在海蝕洞深處或沉船的船艙裡，夜裡伸出觸腕，在礁石間摸找蟹、魚與貝類。"
        "牠能以水屬性力量讓海水沿著觸腕裹成一層沉重的水套，離開海面一整個潮汐仍保持濕潤，還能拖著身體爬上崖腳的礁岩。"
        "南潮港一帶的漁家熟知哪幾處海蝕洞有牠出沒，收漁籠時會繞開那些洞口。"
        "牠以單條觸腕纏住一名對手絞緊，也會甩開全部觸腕橫掃身旁每個對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體盤踞在一艘舊商船的殘骸裡，總是纏著船上那具生鏽的大錨，被稱為「沉錨」。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；觸腕水套之力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨型章魚：水屬性只在自身觸腕裹成水套，讓牠離水時保持濕潤並加重擊打，不掀起浪潮、不拖沉船隻、不操控海流；戰鬥呈現為水屬性物理絞纏與範圍橫掃，資源耗盡後回到普通攻擊。不具神性、守護使命或精靈關聯，也不屬於遠洋魔獸。連結南潮港漁家收漁籠的習慣與海崖下的沉船。",
        "（作者私有：尚未證實的猜想）南潮港的老船匠說沉錨纏著的那具大錨來自一艘載滿精工銀器的商船，這種說法尚未證實。",
        "wreck_den_elder",
        True,
    ),
    MonsterSpecies(
        "shaft_leap_cricket",
        "坑道灶馬",
        "坑道灶馬是約手掌長的穴居蟋蟀類魔獸，成群棲息於西部丘陵的礦坑坑道、作坊地窖與磨坊的倉房。",
        "淺褐色的身體向上拱起，光滑的外殼帶著深色斑紋。"
        "觸角比身體長上好幾倍，後腿粗壯修長，大腿鼓起，小腿上排著細刺。",
        "牠們躲在陰暗潮濕的角落，夜裡成群爬出，啃食皮革、蠟燭的油脂、麵粉與穀屑，也會聚到礦工的燈旁。"
        "牠的後腿帶著異常的彈力，一蹬就能在漆黑的坑道裡躍出十幾步遠，落地後立刻又縮起後腿準備下一跳。"
        "西部丘陵的作坊與磨坊多半挖有地窖存放皮料與麵粉，坑道灶馬一旦在地窖裡繁衍開來，就會咬壞水車的皮帶與麵粉袋。"
        "近身時，牠以後腿猛力蹬踢對手，蹬踢時後腿順勢縮起蓄力，短時間內身形更加靈活。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；後腿異常彈力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居灶馬：後腿彈力屬於身體能力，不帶元素、不發出鳴聲干擾；戰鬥呈現為蹬踢與自身短暫敏捷提升。描寫維持昆蟲體態。連結礦坑坑道、作坊地窖與磨坊水車的皮帶。",
        "（作者私有：尚未證實的猜想）灰岩城的礦工說坑道灶馬成群往坑口爬的日子，坑道深處就會滲水，這種說法尚未證實。",
        "cellar_leaper",
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
        MonsterCombatProfile(
            hp=30, mp=20, sp=8, atk_phys=4, agility=7, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("grain_shaking_peck",),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "flock_leader",
        "sway_whistle_sparrow",
        "領群型",
        "以鳴聲協調同伴，從不同方向干擾驅趕者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=55, mp=30, sp=12, atk_phys=8, agility=10, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("grain_shaking_peck",),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "shore_walker",
        "tide_lamp_crab",
        "灘行型",
        "普通版本，遇人多半退避。",
        "low",
        True,
        MonsterCombatProfile(
            hp=30, mp=20, sp=9, atk_phys=5, agility=4, defense=5, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("lamp_carapace_claw",),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "reef_warden",
        "tide_lamp_crab",
        "守礁型",
        "占據狹窄洞口，利用地形保護族群。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=15, atk_phys=12, agility=4, defense=7, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("lamp_carapace_claw",),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "burrow_maker",
        "ridge_burrow_hare",
        "掘巢型",
        "普通版本，依靠洞道逃避。",
        "low",
        True,
        MonsterCombatProfile(
            hp=30, mp=20, sp=9, atk_phys=4, agility=8, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("ridge_bracing_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "nest_guard",
        "ridge_burrow_hare",
        "護巢型",
        "加固入口，在窄處阻擋侵入者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=55, mp=30, sp=15, atk_phys=11, agility=6, defense=6, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("ridge_bracing_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "cliff_stepper",
        "rock_echo_goat",
        "踏崖型",
        "普通版本，偏向逃往高處。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=130, mp=30, sp=20, atk_phys=20, agility=16, defense=12, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("rock_echo_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "pass_warden",
        "rock_echo_goat",
        "守隘型",
        "守住岩坡入口，將衝撞與落石結合。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=170, mp=50, sp=30, atk_phys=26, agility=14, defense=14, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("rock_echo_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "wood_stalker",
        "fog_mane_lynx",
        "林伏型",
        "普通版本，守候林間獵徑。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=115, mp=30, sp=20, atk_phys=20, agility=20, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("mane_crosswind_pounce",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "trail_hunter",
        "fog_mane_lynx",
        "獵道型",
        "反覆試探隊伍邊緣，專挑落單的馱獸下手。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=165, mp=50, sp=30, atk_phys=25, agility=22, defense=12, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("mane_crosswind_pounce",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "bank_lurker",
        "tide_devouring_crocodile",
        "潛岸型",
        "普通版本，守候野生動物渡水處。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=140, mp=30, sp=40, atk_phys=22, agility=12, defense=14, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("tide_devouring_bite",),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "bay_warden",
        "tide_devouring_crocodile",
        "守灣型",
        "占據有遮蔽的泊岸入口，阻礙小船靠岸。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=210, mp=50, sp=60, atk_phys=28, agility=12, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("tide_devouring_bite",),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "mudbank_dweller",
        "mudfilm_slime",
        "濕岸型",
        "普通版本，貼著潮濕溝岸與滲水洞口覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=60, mp=0, sp=12, atk_phys=4, agility=3, defense=7, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mudfilm_guard",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "wax_cache_forager",
        "wax_pouch_rat",
        "藏穀型",
        "普通版本，以頰囊蠟膜裹住穀粒，藏進潮濕巢穴。",
        "low",
        True,
        MonsterCombatProfile(
            hp=45, mp=0, sp=14, atk_phys=6, agility=9, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("wax_pouch_slip",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "hanging_nest_forager",
        "sticky_palm_goblin",
        "懸巢型",
        "普通版本，在岩棚與灌木間搬運巢材、維護懸掛巢。",
        "low",
        True,
        MonsterCombatProfile(
            hp=38, mp=0, sp=12, atk_phys=7, agility=11, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("sticky_palm_grab",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "reservoir_warden",
        "tide_devouring_crocodile",
        "蓄潮型",
        "蓄潮型長期占據偏遠潮汐支流的深灣，利用退潮後留下的窄水道伏擊。"
        "頸側與背脊的發達皺褶維持著薄水膜，咬合接觸活物時吸取部分魔力，"
        "再將自身魔力投入短暫護膜。",
        "high",
        False,
        MonsterCombatProfile(
            hp=520, mp=40, sp=40, atk_phys=32, agility=18, defense=24, magic_power=0
        ),
        "A",
        True,
        active_skill_keys=("tide_devouring_bite", "reservoir_guard"),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "warm_den_boar",
        "ember_bristle_boar",
        "焙窩型",
        "普通版本，反覆使用烘乾的泥窩與固定覓食路線。",
        "high",
        True,
        MonsterCombatProfile(
            hp=380, mp=36, sp=20, atk_phys=28, agility=17, defense=20, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("ember_tusk_charge", "ember_bristle_sweep"),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "rotlog_sprout",
        "spore_cap_mushroom",
        "腐木型",
        "普通版本，成群附著在倒木上，緩慢挪動覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=40, mp=20, sp=8, atk_phys=5, agility=3, defense=5, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("spore_puff_bump",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "ring_elder",
        "spore_cap_mushroom",
        "菌環型",
        "生長在林間菌環中央的老個體，菌傘更寬、孢粉更濃，守著整圈菌群。",
        "low",
        False,
        MonsterCombatProfile(
            hp=62, mp=30, sp=12, atk_phys=9, agility=4, defense=7, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("spore_puff_bump",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "quill_forager",
        "moss_quill_porcupine",
        "啃皮型",
        "普通版本，夜間沿固定路線啃食樹皮與嫩根。",
        "low",
        True,
        MonsterCombatProfile(
            hp=44, mp=20, sp=9, atk_phys=6, agility=5, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("quill_brace_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "den_sentry",
        "moss_quill_porcupine",
        "守洞型",
        "帶著幼獸占據倒木空洞的個體，棘根苔層更厚，守在洞口正面迎向來者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=66, mp=30, sp=15, atk_phys=11, agility=5, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("quill_brace_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "hollow_roost_flier",
        "hollow_tree_bat",
        "棲洞型",
        "普通版本，成群棲息於中空樹幹，黃昏外出覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=28, mp=20, sp=6, atk_phys=5, agility=11, defense=2, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("hollow_bat_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "colony_sentinel",
        "hollow_tree_bat",
        "哨群型",
        "棲群中體型最大的個體，守在樹洞口最先迎向闖入者，以尖銳叫聲召回同伴。",
        "low",
        False,
        MonsterCombatProfile(
            hp=50, mp=30, sp=10, atk_phys=9, agility=12, defense=3, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("hollow_bat_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "hush_wing_hunter",
        "hush_wing_owl",
        "夜獵型",
        "普通版本，在黃昏與深夜沿林冠獵捕。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=120, mp=30, sp=20, atk_phys=21, agility=22, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("hush_wing_swoop",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "old_hollow_owl",
        "hush_wing_owl",
        "古巢型",
        "長年占據同一株巨木樹洞的老個體，育雛期間會撲向靠近巢樹的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=160, mp=50, sp=30, atk_phys=26, agility=24, defense=12, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("hush_wing_swoop",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "vine_weaver",
        "vine_net_spider",
        "織藤型",
        "普通版本，守在獸徑旁的藤網邊等待獵物。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=19, agility=15, defense=12, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("vine_thread_cast",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "trail_netter",
        "vine_net_spider",
        "封道型",
        "把藤網一路織到人走的林道上，占據整段通道的大型個體。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=25, agility=17, defense=14, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("vine_thread_cast",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "wood_crown_elder",
        "moss_crown_stag",
        "老冠型",
        "普通版本，每年在同一片林間空地度過發情期的老雄鹿。",
        "high",
        True,
        MonsterCombatProfile(
            hp=460, mp=48, sp=30, atk_phys=32, agility=18, defense=26, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("moss_crown_charge", "moss_crown_sweep",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "seep_sipper",
        "mist_spring_frog",
        "汲泉型",
        "普通版本，成群貼在泉眼周圍的岩壁上吸取霧氣。",
        "low",
        True,
        MonsterCombatProfile(
            hp=34, mp=20, sp=6, atk_phys=5, agility=8, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mist_tongue_sip",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "spring_keeper",
        "mist_spring_frog",
        "泉主型",
        "占據一整處泉池的老個體，體型大上一倍，喉囊鳴聲能壓過整群同伴。",
        "low",
        False,
        MonsterCombatProfile(
            hp=58, mp=30, sp=10, atk_phys=9, agility=8, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mist_tongue_sip",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "ledge_basker",
        "warm_rock_salamander",
        "曬岩型",
        "普通版本，白天趴在向陽岩面上曬太陽，清晨出來捕食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=36, mp=20, sp=9, atk_phys=6, agility=5, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("ember_skin_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "vent_crack_dweller",
        "warm_rock_salamander",
        "熱縫型",
        "長年住在山腰地熱裂縫旁的大型個體，皮膚斑點終日微亮，咬勁更強。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=15, atk_phys=10, agility=6, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("ember_skin_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "updraft_glider",
        "bone_breaker_vulture",
        "盤谷型",
        "普通版本，在雲霧上方的上升氣流裡盤旋，尋找獸骨。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=135, mp=30, sp=20, atk_phys=21, agility=17, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("grit_wing_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "crag_nest_vulture",
        "bone_breaker_vulture",
        "崖巢型",
        "孵育期守在巢邊岩棚的個體，會連續俯衝驅趕靠近巢崖的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=180, mp=50, sp=30, atk_phys=26, agility=18, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("grit_wing_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "lamp_seeker",
        "mist_lamp_moth",
        "逐光型",
        "普通版本，入夜後循著光亮在霧中飛行。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=115, mp=30, sp=16, atk_phys=18, agility=19, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("veil_scale_flutter",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "old_veil_moth",
        "mist_lamp_moth",
        "老翅型",
        "翅膀磨得破舊、體型最大的老個體，整夜守著同一盞燈火撲飛。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=150, mp=50, sp=24, atk_phys=23, agility=21, defense=11, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("veil_scale_flutter",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "white_rime_coil",
        "rime_scale_serpent",
        "霜谷型",
        "普通版本，盤踞同一座霧谷多年的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=500, mp=48, sp=30, atk_phys=31, agility=20, defense=24, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("rime_fang_strike", "rime_tail_lash",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "pine_floor_grouse",
        "drum_wing_grouse",
        "林床型",
        "普通版本，成群在林床上啄食松針與漿果。",
        "low",
        True,
        MonsterCombatProfile(
            hp=32, mp=20, sp=6, atk_phys=4, agility=9, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("drum_wing_burst",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "lek_master_cock",
        "drum_wing_grouse",
        "領場型",
        "在求偶場中央占據最好位置的老雄雞，尾扇最寬，會撲向走進求偶場的任何身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=56, mp=30, sp=10, atk_phys=9, agility=11, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("drum_wing_burst",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "dam_builder",
        "mud_dam_beaver",
        "築壩型",
        "普通版本，以家族為單位在溪流上築壩、啃樹。",
        "low",
        True,
        MonsterCombatProfile(
            hp=46, mp=20, sp=9, atk_phys=5, agility=4, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mud_pelt_slap",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "old_dam_keeper",
        "mud_dam_beaver",
        "老壩型",
        "守著家族最老水壩的大型個體，毛皮上的泥層最厚，會正面迎向靠近水壩的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=68, mp=30, sp=15, atk_phys=10, agility=4, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mud_pelt_slap",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "vein_digger",
        "ore_vein_mole",
        "掘脈型",
        "普通版本，沿著礦脈下方的鬆土挖掘隧道覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=36, mp=20, sp=8, atk_phys=6, agility=5, defense=4, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("grit_claw_scrape",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "deep_seam_mole",
        "ore_vein_mole",
        "深脈型",
        "在礦脈深處挖出寬大巢室的老個體，前爪磨得發亮，會從隧道口迎向闖入者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=12, atk_phys=10, agility=6, defense=7, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("grit_claw_scrape",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "trapline_raider",
        "cache_raider_wolverine",
        "掠索型",
        "普通版本，沿著獵人的陷阱線一路吃掉夾到的獵物。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=140, mp=0, sp=24, atk_phys=22, agility=14, defense=13, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("jaw_lock_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "winter_den_glutton",
        "cache_raider_wolverine",
        "冬穴型",
        "入冬前把整季食物藏進雪下巢穴的個體，守著儲糧，會撲向靠近巢穴的任何身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=190, mp=0, sp=36, atk_phys=27, agility=15, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("jaw_lock_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "windcrest_elder",
        "ore_nest_griffin",
        "巔巢型",
        "普通版本，占據同一座礦脈高崖多年的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=430, mp=48, sp=30, atk_phys=33, agility=26, defense=21, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("ore_crest_dive", "ore_crest_gale",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "road_ball_roller",
        "clod_ball_beetle",
        "滾球型",
        "普通版本，成對推著土球在牧場與官道之間來回。",
        "low",
        True,
        MonsterCombatProfile(
            hp=38, mp=20, sp=9, atk_phys=5, agility=4, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("clod_ball_shove",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "heap_brood_keeper",
        "clod_ball_beetle",
        "育堆型",
        "守著牧場邊一整座育幼土堆的大型個體，甲殼最厚，會正面頂撞靠近土堆的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=15, atk_phys=10, agility=4, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("clod_ball_shove",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "plain_runner",
        "dust_mane_horse",
        "奔原型",
        "普通版本，成小群在草原上吃草、奔馳。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=150, mp=30, sp=20, atk_phys=21, agility=20, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("dust_gallop_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "herd_stallion",
        "dust_mane_horse",
        "頭馬型",
        "帶領整群野馬的成年公馬，體型最大，會擋在馬群前方迎向靠近的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=200, mp=50, sp=30, atk_phys=26, agility=22, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("dust_gallop_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
    MonsterVariant(
        "sluice_wader",
        "sluice_spear_heron",
        "涉渠型",
        "普通版本，獨自守在灌溉渠的水門下捕魚。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=22, agility=18, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("spear_beak_jab",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "heronry_elder",
        "sluice_spear_heron",
        "林巢型",
        "在渠邊柳林裡帶領整片鷺巢的老個體，孵育期會連續刺向走近巢樹的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=26, agility=19, defense=12, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("spear_beak_jab",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "wide_mound_elder",
        "lake_mound_turtle",
        "丘背型",
        "普通版本，背甲泥層積了多年、長滿蘆葦的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=500, mp=48, sp=30, atk_phys=32, agility=16, defense=30, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("lake_mound_bite", "lake_mound_quake",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "mudflat_skipper",
        "flat_leap_goby",
        "跳灘型",
        "普通版本，成群在退潮後的泥灘上爬行、啃藻。",
        "low",
        True,
        MonsterCombatProfile(
            hp=32, mp=0, sp=9, atk_phys=5, agility=10, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mud_tail_flick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "turret_keeper",
        "flat_leap_goby",
        "築塔型",
        "在洞口堆起泥塔、守著一片泥灘的大型雄魚，會跳向任何走近泥塔的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=55, mp=0, sp=15, atk_phys=9, agility=10, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mud_tail_flick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "mast_circler",
        "mast_wind_gull",
        "繞桅型",
        "普通版本，成群在港口的桅杆之間盤旋、搶食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=28, mp=20, sp=9, atk_phys=5, agility=11, defense=2, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("wind_snatch_dive",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "stack_colony_elder",
        "mast_wind_gull",
        "堤群型",
        "在防波堤礁石上帶領整片鷗群的老個體，會帶頭撲向靠近繁殖礁石的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=50, mp=30, sp=15, atk_phys=9, agility=12, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("wind_snatch_dive",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "pier_basker",
        "breakwater_seal",
        "曬堤型",
        "普通版本，退潮後成群爬上防波堤與礁岩曬太陽。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=160, mp=0, sp=24, atk_phys=21, agility=12, defense=13, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("flipper_slide_slam",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "haulout_bull",
        "breakwater_seal",
        "霸灘型",
        "占住整片沙洲、帶著一群母海豹的大型公海豹，會滑向任何踏上沙洲的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=215, mp=0, sp=36, atk_phys=26, agility=12, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("flipper_slide_slam",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "salt_hauler",
        "salt_column_ant",
        "搬鹽型",
        "普通版本，排成長列在鹽道與曬鹽場之間搬運鹽粒。",
        "low",
        True,
        MonsterCombatProfile(
            hp=34, mp=0, sp=9, atk_phys=5, agility=8, defense=4, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("salt_jaw_haul",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "salt_mound_soldier",
        "salt_column_ant",
        "守丘型",
        "頭部特別大、大顎特別寬的兵蟻，守在結著鹽殼的巢丘上，會咬向任何踩上巢丘的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=58, mp=0, sp=15, atk_phys=10, agility=7, defense=6, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("salt_jaw_haul",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "oyster_rack_creeper",
        "stiff_arm_starfish",
        "爬架型",
        "普通版本，成片爬過潮池礁石與蚵架，扳開貝殼覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=40, mp=0, sp=9, atk_phys=4, agility=3, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("stiff_arm_press",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "tide_pool_elder",
        "stiff_arm_starfish",
        "老礁型",
        "占住崖腳一座深潮池的老個體，腕足最粗、硬疣最厚，會撲向任何涉進潮池的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=64, mp=0, sp=15, atk_phys=9, agility=3, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("stiff_arm_press",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "reef_burrow_striker",
        "shell_crack_shrimp",
        "穴擊型",
        "普通版本，守在淺灘與礁縫的洞口伏擊路過的蟹貝。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=24, agility=18, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("club_limb_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "seawall_den_holder",
        "shell_crack_shrimp",
        "深穴型",
        "在港口石砌海堤裡挖出深穴的大型老個體，捕肢最粗，會擊向任何在洞口前停步的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=28, agility=18, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("club_limb_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "seacliff_basker",
        "salt_snort_iguana",
        "曬崖型",
        "普通版本，成群趴在曬暖的崖石上，退潮時潛到崖腳啃食海藻。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=150, mp=0, sp=24, atk_phys=20, agility=12, defense=14, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("brine_snort_butt",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "salt_dike_holder",
        "salt_snort_iguana",
        "冠刺型",
        "背刺最高、鹽殼最厚的大型雄蜥，帶著一群母蜥占住曬鹽場最溫暖的一段堤面，會頂向任何走上那段堤面的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=205, mp=0, sp=36, atk_phys=25, agility=12, defense=16, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("brine_snort_butt",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "wreck_den_elder",
        "wreck_arm_octopus",
        "沉骸型",
        "普通版本，長年盤踞在海蝕洞或沉船殘骸裡的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=480, mp=48, sp=30, atk_phys=31, agility=22, defense=22, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("wreck_arm_bind", "wreck_arm_sweep",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
    MonsterVariant(
        "cellar_leaper",
        "shaft_leap_cricket",
        "躍窖型",
        "普通版本，成群躲在地窖與坑道的陰暗角落，夜裡出來覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=30, mp=0, sp=9, atk_phys=5, agility=11, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("coiled_hind_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
    MonsterVariant(
        "old_shaft_leaper",
        "shaft_leap_cricket",
        "守坑型",
        "住在廢棄礦坑口、後腿最長的老個體，坑口一有燈光靠近，就帶著整群躍出。",
        "low",
        False,
        MonsterCombatProfile(
            hp=52, mp=0, sp=15, atk_phys=9, agility=12, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("coiled_hind_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
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
