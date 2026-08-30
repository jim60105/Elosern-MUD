"""Fixed-title lore registry for the title system (title-system D2/D3).

Two kinds of player-facing titles exist: deterministic **fixed titles** granted
by rule predicates (this registry) and player-voted **epithets** (nomination
system, change G). This module holds the frozen ``FixedTitleDef`` registry,
the declarative predicate families it validates against, and the
``STARTER_EPITHET`` constant every character receives on guild registration
(D8, ``title-fixed-core`` DF4). The deterministic grants themselves live in
``world/rules/titles.py``; this module is read-only registry data.
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .guild import GUILD_RANK_REGISTRY
from .monsters import MONSTER_TIER_REGISTRY
from .elements import ELEMENT_REGISTRY


# The wire bound every presenter enforces on ``full_title`` is 128 code
# points (``web.webclient.presentation.character.MAX_FULL_TITLE_CODE_POINTS``
#). Registry displays are capped so fixed + separator + maximum epithet
# composes to exactly that bound: a legitimate write can never overflow the
# panel protocol.
MAX_TITLE_DISPLAY_CODE_POINTS = 63


class TitleCategory(StrEnum):
    """The closed display taxonomy of the fixed-title codex (D7)."""

    COMBAT = "combat"
    SPELL = "spell"
    EXPLORE = "explore"
    GUILD = "guild"
    ROMANCE = "romance"


class TitlePredicateFamily(StrEnum):
    """The closed declarative predicate family set (D2 §6.2).

    Every family carries parameters only; evaluation is implemented in
    ``world.rules.titles`` (the title event-effect planner), never here.
    """

    LINEAGE_COMPLETE = "lineage_complete"
    MASTERY_OWNED = "mastery_owned"
    FIRST_KILL_TIER = "first_kill_tier"
    QUEST_COMPLETED = "quest_completed"
    GUILD_RANK_REACHED = "guild_rank_reached"
    SEXUAL_EXPERIENCE = "sexual_experience"
    COUNTER_THRESHOLD = "counter_threshold"


# The single parameter field each family may carry, keyed by family. Load
# validation enforces exactly this mapping, so a row can never carry a
# parameter its family does not use or omit one it requires.
_FAMILY_PARAMETER: dict[TitlePredicateFamily, str] = {
    TitlePredicateFamily.LINEAGE_COMPLETE: "root_skill_key",
    TitlePredicateFamily.MASTERY_OWNED: "element",
    TitlePredicateFamily.FIRST_KILL_TIER: "monster_tier",
    TitlePredicateFamily.QUEST_COMPLETED: "quest_key",
    TitlePredicateFamily.GUILD_RANK_REACHED: "guild_rank",
    TitlePredicateFamily.SEXUAL_EXPERIENCE: "experience_type",
    TitlePredicateFamily.COUNTER_THRESHOLD: "counter",
}


@dataclass(frozen=True, slots=True)
class TitlePredicate:
    """One declarative predicate with family-specific parameters only.

    The family selects the face the single parameter is validated against:
    ``lineage_complete`` → a skill registry root key; ``mastery_owned`` → an
    element key; ``first_kill_tier`` → a monster threat tier;
    ``quest_completed`` → a quest definition key; ``guild_rank_reached`` → a
    guild rank key; ``sexual_experience`` → an experience type member;
    ``counter_threshold`` → a sexual lifetime counter name plus an int
    threshold. Exactly one family/parameter group is valid per predicate.
    """

    family: TitlePredicateFamily
    root_skill_key: str | None = None
    element: str | None = None
    monster_tier: str | None = None
    quest_key: str | None = None
    guild_rank: str | None = None
    experience_type: str | None = None
    counter: str | None = None
    threshold: int | None = None


@dataclass(frozen=True, slots=True)
class FixedTitleDef:
    """One immutable fixed-title row (key, display, category, prose, hint)."""

    key: str
    display_name_zh: str
    category: TitleCategory
    flavor_zh: str
    hint_zh: str
    predicate: TitlePredicate


@dataclass(frozen=True, slots=True)
class StarterEpithet:
    """The deterministic onboarding epithet (D8 §6.5): display plus basis."""

    display: str
    origin_basis: str


STARTER_EPITHET = StarterEpithet(
    "南門新客",
    "你在南門守衛的目送下踏入阿爾托利亞，成為公會的新面孔。",
)


def _predicate(
    family: TitlePredicateFamily,
    **kwargs: str | int,
) -> TitlePredicate:
    return TitlePredicate(
        family=family,
        **{key: value for key, value in kwargs.items() if value is not None},
    )


# Authorized content: the seven guild-rank pairings (D3). Each row pairs the
# ``GUILD_RANK_REGISTRY`` row named by its predicate; the transactional grants
# (``register_adventurer`` / ``settle_exam_outcome``) ride the rank-change
# transactions, and the planner's ``guild_rank_reached`` evaluation is a
# dedupe-level no-op in practice. Predicate rows beyond the guild pairings are
# future content work (design §6.2 note).
_FIXED_TITLE_ROWS: dict[str, FixedTitleDef] = {
    "g_f_rank": FixedTitleDef(
        "g_f_rank",
        "F級冒險者",
        TitleCategory.GUILD,
        "你在公會名冊上留下第一個名字，冒險者的旅程由此開始。",
        "完成公會註冊即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="F"),
    ),
    "g_e_rank": FixedTitleDef(
        "g_e_rank",
        "E級斥候",
        TitleCategory.GUILD,
        "你踏足荒野、獵殺低階魔物，成了公會眼中可靠的斥候。",
        "通過 E 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="E"),
    ),
    "g_d_rank": FixedTitleDef(
        "g_d_rank",
        "D級傭兵",
        TitleCategory.GUILD,
        "你已能獨當一面接下委託，傭兵的名號隨之遠播。",
        "通過 D 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="D"),
    ),
    "g_c_rank": FixedTitleDef(
        "g_c_rank",
        "C級騎士",
        TitleCategory.GUILD,
        "你以劍與魔法守護委託與弱者，被賦予騎士之銜。",
        "通過 C 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="C"),
    ),
    "g_b_rank": FixedTitleDef(
        "g_b_rank",
        "B級英雄",
        TitleCategory.GUILD,
        "高難度委託對你已成日常，坊間開始以英雄稱呼你。",
        "通過 B 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="B"),
    ),
    "g_a_rank": FixedTitleDef(
        "g_a_rank",
        "A級傳奇",
        TitleCategory.GUILD,
        "你的事蹟被吟遊詩人寫入歌謠，傳奇之名實至名歸。",
        "通過 A 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="A"),
    ),
    "g_s_rank": FixedTitleDef(
        "g_s_rank",
        "S級傳說",
        TitleCategory.GUILD,
        "凌駕人類領域的委託也只有你能接下，傳說由你書寫。",
        "通過 S 級公會考核即可獲得。",
        _predicate(TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank="S"),
    ),
}

# The published registry is a read-only proxy: every consumer reads through
# ``.get`` / ``.values`` / ``[key]`` / ``in``, and no subsystem may mutate lore
# data in place.
FIXED_TITLE_REGISTRY = MappingProxyType(_FIXED_TITLE_ROWS)


class TitleRegistryError(ValueError):
    """A fixed-title registry row violates the closed load contract."""


def validate_fixed_titles(
    entries: list[FixedTitleDef],
    *,
    elements: set[str] | None = None,
    monster_tiers: set[str] | None = None,
    guild_ranks: set[str] | None = None,
    quest_keys: set[str] | None = None,
    experience_types: set[str] | None = None,
    skill_keys: set[str] | None = None,
) -> None:
    """Raise ``TitleRegistryError`` unless every row is fully valid.

    Pure validation with injectable faces so tests can exercise a dangling
    reference without mutating the shipped registry. Called at import time
    (and by tests) with the live registries; a violation names the offending
    row's key and the dangling reference.
    """
    entries = list(entries)
    seen: set[str] = set()
    predicates: list[TitlePredicate] = []
    for entry in entries:
        if not isinstance(entry, FixedTitleDef):
            raise TitleRegistryError("registry holds a non-FixedTitleDef row")
        if entry.key in seen:
            raise TitleRegistryError(f"duplicate fixed-title key {entry.key!r}")
        seen.add(entry.key)
        if not isinstance(entry.key, str) or not entry.key:
            raise TitleRegistryError("fixed-title key must be a non-empty string")
        if not isinstance(entry.display_name_zh, str) or not entry.display_name_zh:
            raise TitleRegistryError(f"{entry.key!r}: display_name_zh must be non-empty")
        if not isinstance(entry.flavor_zh, str) or not entry.flavor_zh:
            raise TitleRegistryError(f"{entry.key!r}: flavor_zh must be non-empty")
        if not isinstance(entry.hint_zh, str) or not entry.hint_zh:
            raise TitleRegistryError(f"{entry.key!r}: hint_zh must be non-empty")
        if not isinstance(entry.category, TitleCategory):
            raise TitleRegistryError(
                f"{entry.key!r}: category must be a TitleCategory member"
            )
        predicate = entry.predicate
        if not isinstance(predicate, TitlePredicate):
            raise TitleRegistryError(f"{entry.key!r}: predicate must be a TitlePredicate")
        predicates.append(predicate)

    families = {predicate.family for predicate in predicates}
    unknown = families - set(TitlePredicateFamily)
    if unknown:
        names = ", ".join(sorted(str(family) for family in unknown))
        raise TitleRegistryError(f"unknown predicate family: {names}")

    # Equip-identifier resolution: ``equip_fixed`` accepts a registry key or a
    # display name, so a duplicate display or a key colliding with another
    # row's display makes equip ambiguous. Displays are additionally bounded
    # so a composed full title cannot overflow the wire bound on its half.
    seen_displays: dict[str, str] = {}
    for entry in entries:
        display = entry.display_name_zh
        if len(display) > MAX_TITLE_DISPLAY_CODE_POINTS:
            raise TitleRegistryError(
                f"title display exceeds {MAX_TITLE_DISPLAY_CODE_POINTS} "
                f"code points: {entry.key}"
            )
        if display in seen_displays:
            raise TitleRegistryError(
                f"title display collision: {entry.key} duplicates "
                f"{seen_displays[display]}"
            )
        seen_displays[display] = entry.key
    for entry in entries:
        owner = seen_displays.get(entry.key)
        if owner is not None and owner != entry.key:
            raise TitleRegistryError(
                f"title key collision: {entry.key} is also the display of "
                f"{owner}"
            )

    # Parameter-shape validation: exactly the family's declared parameter may
    # be set, and `counter_threshold` additionally requires an integer
    # threshold. Names the row so the violation is immediately actionable.
    for entry in entries:
        predicate = entry.predicate
        parameter = _FAMILY_PARAMETER[predicate.family]
        supplied = {
            name: getattr(predicate, name)
            for name in (
                "root_skill_key",
                "element",
                "monster_tier",
                "quest_key",
                "guild_rank",
                "experience_type",
                "counter",
            )
            if getattr(predicate, name) is not None
        }
        extras = set(supplied) - {parameter}
        if extras:
            raise TitleRegistryError(
                f"{entry.key!r}: family {predicate.family.value} carries "
                f"unexpected parameters {sorted(extras)}"
            )
        if parameter not in supplied:
            raise TitleRegistryError(
                f"{entry.key!r}: family {predicate.family.value} requires "
                f"{parameter!r}"
            )
        if predicate.family is TitlePredicateFamily.COUNTER_THRESHOLD:
            if isinstance(predicate.threshold, bool) or not isinstance(
                predicate.threshold, int
            ):
                raise TitleRegistryError(
                    f"{entry.key!r}: counter_threshold requires an integer "
                    "threshold"
                )
            if predicate.threshold < 1:
                raise TitleRegistryError(
                    f"{entry.key!r}: counter_threshold must be >= 1"
                )
        elif predicate.threshold is not None:
            raise TitleRegistryError(
                f"{entry.key!r}: threshold is only valid for counter_threshold"
            )
        value = supplied[parameter]
        if not isinstance(value, str) or not value:
            raise TitleRegistryError(
                f"{entry.key!r}: {parameter} must be a non-empty string"
            )

    # Face membership: every referenced parameter must resolve against the
    # injected face set. A dangling reference names the row and the face.
    faces: dict[str, tuple[str, set[str]]] = {
        "root_skill_key": ("skill registry", skill_keys or set()),
        "element": ("element registry", elements or set()),
        "monster_tier": ("monster tier registry", monster_tiers or set()),
        "quest_key": ("quest definition registry", quest_keys or set()),
        "guild_rank": ("guild rank registry", guild_ranks or set()),
        "experience_type": ("sexual experience types", experience_types or set()),
    }
    for entry in entries:
        predicate = entry.predicate
        parameter = _FAMILY_PARAMETER[predicate.family]
        if parameter == "counter":
            continue
        face_name, face = faces[parameter]
        value = getattr(predicate, parameter)
        if value not in face:
            raise TitleRegistryError(
                f"{entry.key!r}: predicate references unknown "
                f"{face_name} {value!r}"
            )


def _live_faces() -> dict[str, set[str]]:
    """Resolve the current registry faces for the shipped content.

    Static lore faces (guild ranks, monster tiers, elements) import directly;
    runtime-populated faces (quest definitions, skill registry, sexual
    experience types) are imported lazily so this module stays importable
    before those registries fill (e.g. at server-start lore sync).
    """
    faces = {
        "elements": {element.key for element in ELEMENT_REGISTRY.values()},
        "monster_tiers": set(MONSTER_TIER_REGISTRY),
        "guild_ranks": set(GUILD_RANK_REGISTRY),
    }
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY

    faces["quest_keys"] = set(QUEST_DEFINITION_REGISTRY)
    from world.skills.registry import SKILL_REGISTRY

    faces["skill_keys"] = set(SKILL_REGISTRY)
    from world.rules.rulebook.schema import load_rules
    from world.rules.sexual_transitions import _RULE_PATH

    faces["experience_types"] = {
        rule.then["add"]
        for rule in load_rules(_RULE_PATH)
        if rule.then.get("field") == "experience_types"
        and isinstance(rule.then.get("add"), str)
    }
    return faces


# Shipped content must be valid the moment the module loads; the seven guild
# rows only reference the static guild-rank face, so boot-time validation is
# deterministic and independent of startup sync order.
# The concrete dict is validated (and then published through the proxy), so a
# row is checked against the real data before anything can observe it.
validate_fixed_titles(
    list(_FIXED_TITLE_ROWS.values()),
    **{
        key: value
        for key, value in _live_faces().items()
        if key in ("elements", "monster_tiers", "guild_ranks")
    },
)