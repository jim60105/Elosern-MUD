"""Skill definitions from design section 5.2 and ``skills-equipment``.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. Every ``effects`` string is
parsed into a typed dataclass by ``world.skills.effects.parse_effect`` at
construction; see that module for the recognized effect-ID conventions.
"""

from dataclasses import dataclass
from enum import StrEnum

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import HealEffect, parse_effect


class _FrozenDict(dict):
    """A ``dict`` preserving the exact field contract without mutation."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("skill definition collections are immutable")

    __delitem__ = _immutable
    __ior__ = _immutable
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


class _FrozenList(list):
    """A ``list`` preserving the exact field contract without mutation."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("skill definition collections are immutable")

    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    __setitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable


class SkillKind(StrEnum):
    """Whether a skill is invoked or continuously owned."""

    ACTIVE = "active"
    PASSIVE = "passive"


class TargetSpec(StrEnum):
    """The target cardinality expected by the future action resolver."""

    NONE = "none"
    SELF = "self"
    SINGLE = "single"
    AREA = "area"


class FactionConstraint(StrEnum):
    """Relations a skill permits the resolver to target.

    ``ANY`` (the default) and ``SELF_ONLY`` are the only constraints shipped
    content may declare: every attack and recovery skill is freely targetable
    among enemies and allies, while a self-only effect restricts its target to
    the actor. ``ALLY`` and ``ENEMY`` are retained as enum values for legacy
    test data; no skill declares them.
    """

    ANY = "any"
    ALLY = "ally"
    ENEMY = "enemy"
    SELF_ONLY = "self_only"


class SkillCategory(StrEnum):
    """Presentation taxonomy for the whole skill registry.

    Declaration order is the display order consumed by the combat panel and
    out-of-combat listing, so it is fixed and must not be reordered. ``group``
    is the optional second level inside a category (an element key for
    ``ELEMENTAL_MAGIC``, a line name for ``SEXUAL_ACT``).
    """

    ELEMENTAL_MAGIC = "elemental_magic"
    MARTIAL_ARTS = "martial_arts"
    ENHANCEMENT = "enhancement"
    INNATE_GIFT = "innate_gift"
    MOVEMENT = "movement"
    DIVINE_MYSTERY = "divine_mystery"
    UTILITY = "utility"
    SEXUAL_ACT = "sexual_act"


# Presentation metadata bounds shared by every immutable skill definition.
LABEL_MAX = 128
DESCRIPTION_MAX = 512


@dataclass(frozen=True)
class SkillDef:
    """Immutable definition of a skill known to deterministic consumers."""

    key: str
    label: str
    description: str
    kind: SkillKind
    target_spec: TargetSpec
    cost: dict[str, int]
    usable_out_of_combat: bool
    element: Element | None
    effects: list[str]
    category: SkillCategory
    group: str | None = None
    faction_constraint: FactionConstraint = FactionConstraint.ANY
    requires_divine_arts: bool = False
    parsed_effects: tuple = ()

    def __post_init__(self) -> None:
        """Enforce the registry invariants for every constructor path.

        Direct ``SkillDef(...)`` construction (for example the production
        ``flee`` definition) must observe the same bounded presentation
        metadata and the same immutable collection contract as the seed
        builder, so no runtime code can mutate a registered definition.
        Every effect string must parse under the typed dispatch table; an
        unrecognized prefix raises here (registry-load time), not at use.
        """
        _validate_metadata(self.label, self.description)
        if self.group is not None and (
            not isinstance(self.group, str) or not self.group.strip()
        ):
            raise ValueError(
                f"skill {self.key!r} declares an invalid group; "
                "group must be a non-empty string when present"
            )
        object.__setattr__(self, "cost", _FrozenDict(self.cost))
        object.__setattr__(self, "effects", _FrozenList(self.effects))
        object.__setattr__(
            self,
            "parsed_effects",
            tuple(parse_effect(effect_id) for effect_id in self.effects),
        )
        self._validate_heal_shape()

    def _validate_heal_shape(self) -> None:
        """Reject a heal shape that contradicts the skill's target spec.

        ``heal:<shape>`` names the cardinality the skill may declare: a single
        heal fits SINGLE or SELF skills, an area heal only AREA skills. Without
        this check the two shapes behave identically (the handler heals whatever
        the pipeline resolved), silently ignoring the declared shape at use time
        — the same class of failure the typed-effect dispatch eliminates.
        """
        for effect in self.parsed_effects:
            if not isinstance(effect, HealEffect):
                continue
            if effect.shape == "single" and self.target_spec not in (
                TargetSpec.SINGLE,
                TargetSpec.SELF,
            ):
                raise ValueError(
                    f"heal:single requires a SINGLE or SELF skill, "
                    f"{self.key!r} declares {self.target_spec.value!r}"
                )
            if effect.shape == "area" and self.target_spec is not TargetSpec.AREA:
                raise ValueError(
                    f"heal:area requires an AREA skill, "
                    f"{self.key!r} declares {self.target_spec.value!r}"
                )


def _validate_metadata(label: str, description: str) -> None:
    """Reject empty or oversized player-facing presentation metadata."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("skill label must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("skill description must be a non-empty string")
    if sum(1 for _ in label) > LABEL_MAX:
        raise ValueError(f"skill label exceeds {LABEL_MAX} code points")
    if sum(1 for _ in description) > DESCRIPTION_MAX:
        raise ValueError(f"skill description exceeds {DESCRIPTION_MAX} code points")


def _skill(
    key: str,
    label: str,
    description: str,
    kind: SkillKind,
    target_spec: TargetSpec,
    *,
    cost: dict[str, int] | None = None,
    usable_out_of_combat: bool = False,
    element: str | None = None,
    effects: list[str] | None = None,
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    requires_divine_arts: bool = False,
    category: SkillCategory,
    group: str | None = None,
) -> SkillDef:
    """Build seed data without duplicating empty collection literals."""
    _validate_metadata(label, description)
    return SkillDef(
        key=key,
        label=label,
        description=description,
        kind=kind,
        target_spec=target_spec,
        cost=_FrozenDict({} if cost is None else cost),
        usable_out_of_combat=usable_out_of_combat,
        element=None if element is None else ELEMENT_REGISTRY[element],
        effects=_FrozenList([] if effects is None else effects),
        faction_constraint=faction_constraint,
        requires_divine_arts=requires_divine_arts,
        category=category,
        group=group,
    )


def _spell(
    key: str,
    label: str,
    description: str,
    target_spec: TargetSpec,
    *,
    mp: int,
    element: str,
    effects: tuple[str, ...],
    usable_out_of_combat: bool = False,
    category: SkillCategory,
    group: str | None = None,
) -> SkillDef:
    """Build one ACTIVE elemental spell — the design doc §4.4 catalog shape.

    Every catalog spell is an ACTIVE skill freely targetable among enemies
    and allies at an integer MP cost, so this helper fixes exactly that
    shape instead of repeating it in each entry.
    """
    return _skill(
        key,
        label,
        description,
        SkillKind.ACTIVE,
        target_spec,
        cost={"mp": mp},
        usable_out_of_combat=usable_out_of_combat,
        element=element,
        effects=list(effects),
        faction_constraint=FactionConstraint.ANY,
        category=category,
        group=group,
    )


def _elemental_spells(
    element: str,
    *spells: tuple[str, str, str, TargetSpec, int, tuple[str, ...]],
) -> tuple[SkillDef, ...]:
    """Build one element's full ACTIVE spell set (design doc §4.4).

    Each row is ``(key, label, description, target_spec, mp, effects)`` in
    the exact order of the design doc's catalog table. The element is written
    once for the whole set. A spell's tier is deliberately NOT a stored
    field: it stays derivable from the set's grouping and each row's MP cost
    band (``spell_tier_for``), per the skill-registry spec.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r} for elemental spell set")
    return tuple(
        _spell(
            key,
            label,
            description,
            target_spec,
            mp=mp,
            element=element,
            effects=effects,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group=element,
        )
        for key, label, description, target_spec, mp, effects in spells
    )


_BODY_TRAITS = ("atk_phys", "agility", "defense")


def _body_multiplier(key: str, label: str, multiplier: float) -> SkillDef:
    """Build one passive physical-stat multiplier tier."""
    return _skill(
        key,
        label,
        "以體內能量強化自身的物理能力，提升攻擊、敏捷與防禦。",
        SkillKind.PASSIVE,
        TargetSpec.SELF,
        usable_out_of_combat=True,
        effects=[
            f"stat_multiply:{trait_key}:{multiplier:g}"
            for trait_key in _BODY_TRAITS
        ],
        category=SkillCategory.ENHANCEMENT,
    )


SKILL_REGISTRY: dict[str, SkillDef] = {
    skill.key: skill
    for skill in (
        _skill(
            "basic_attack",
            "基本攻擊",
            "以普通攻擊對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            element="fire",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:fire:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _body_multiplier("body_enhancement", "身體強化", 100),
        _body_multiplier("body_enhancement_extreme", "身體超強化", 1000),
        _body_multiplier("body_enhancement_basic", "身體強化·初階", 1.2),
        _skill(
            "fire_mastery",
            "火焰精通",
            "被動提昇火焰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="fire",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
        ),
        _skill(
            "dark_mastery",
            "闇屬性精通",
            "被動提昇闇屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="dark",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
        ),
        _skill(
            "wind_mastery",
            "風屬性精通",
            "被動提昇風屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="wind",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
        ),
        _skill(
            "light_mastery",
            "光屬性精通",
            "被動提昇光屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="light",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
        ),
        _skill(
            "water_mastery",
            "水屬性精通",
            "被動提昇水系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="water",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
        ),
        _skill(
            "earth_mastery",
            "土屬性精通",
            "被動提昇土系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="earth",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
        ),
        _skill(
            "lightning_mastery",
            "雷屬性精通",
            "被動提昇雷系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="lightning",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
        ),
        _skill(
            "ice_mastery",
            "冰屬性精通",
            "被動提昇冰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="ice",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
        ),
        *_elemental_spells(
            "fire",
            # 火 — 學徒
            ("fire_ball", "火球術", "凝聚火焰魔力，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 14, ("damage:fire:magic",)),
            ("fire_arrow", "火焰箭", "射出火焰凝聚的箭矢，以低耗能對單一目標造成魔法傷害。", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
            # 火 — 術師
            ("firestorm", "火焰風暴", "召喚覆蓋範圍的火焰風暴，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 30, ("damage:fire:magic",)),
            ("scorching_wave", "灼熱波動", "釋放灼熱的波動，對單一目標造成魔法傷害並使其灼燒。", TargetSpec.SINGLE, 24, ("damage:fire:magic", "buff_apply:fire_scorch")),
            # 火 — 大師
            ("lava_burst", "熔岩術", "使地面迸裂噴出熔岩，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 52, ("damage:fire:magic",)),
            ("infernal_wrap", "業火纏繞", "以業火纏繞單一目標，造成高額魔法傷害。", TargetSpec.SINGLE, 42, ("damage:fire:magic",)),
            # 火 — 賢者
            ("dragon_flame", "龍炎術", "喚起龍之吐息，對範圍內所有目標造成高額魔法傷害。", TargetSpec.AREA, 95, ("damage:fire:magic",)),
            ("hellfire", "煉獄業火", "召喚煉獄的業火，對單一目標造成極高魔法傷害。", TargetSpec.SINGLE, 78, ("damage:fire:magic",)),
            # 火 — 主宰
            ("phoenix_eternal_flame", "不滅鳳凰焰", "召喚不滅的鳳凰之焰，對範圍內所有目標造成極高魔法傷害，並治癒自身。", TargetSpec.AREA, 150, ("damage:fire:magic", "self_heal")),
            ("world_ending_blaze", "焚世終焰", "召喚足以焚盡世界的終焰，對單一目標造成毀滅級魔法傷害。", TargetSpec.SINGLE, 130, ("damage:fire:magic",)),
        ),
        *_elemental_spells(
            "water",
            # 水 — 學徒
            ("water_bolt", "水箭術", "凝聚水之魔力化為箭矢，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 12, ("damage:water:magic",)),
            ("minor_heal", "治癒滴露", "凝聚如滴露般的光芒，恢復單一目標的生命力。", TargetSpec.SINGLE, 11, ("heal:single",)),
            # 水 — 術師
            ("healing_spring", "治癒之泉", "召喚治癒之泉，恢復範圍內所有目標的生命力。", TargetSpec.AREA, 28, ("heal:area",)),
            ("water_shield", "水盾術", "以水之魔力形成護盾，提升單一目標的防禦。", TargetSpec.SINGLE, 22, ("buff_apply:water_shield",)),
            # 水 — 大師
            ("abyssal_whirlpool", "深海漩渦", "召喚深海漩渦，對範圍內所有目標造成魔法傷害並使其束縛。", TargetSpec.AREA, 50, ("damage:water:magic", "buff_apply:water_bind")),
            ("wellspring_of_life", "生命湧泉", "引出生命的湧泉，大量恢復單一目標的生命力。", TargetSpec.SINGLE, 40, ("heal:single",)),
            # 水 — 賢者
            ("tsunami", "海嘯術", "喚起毀滅性的海嘯，對範圍內所有目標造成極高魔法傷害。", TargetSpec.AREA, 95, ("damage:water:magic",)),
            ("tidal_revival", "復生之潮", "召喚復生之潮，大量恢復瀕危目標的生命力。", TargetSpec.SINGLE, 78, ("heal:single",)),
            # 水 — 主宰
            ("sea_of_life", "生命之海", "展開生命之海，大量恢復範圍內所有目標的生命力。", TargetSpec.AREA, 160, ("heal:area",)),
            ("abyssal_tide", "深淵巨潮", "召喚深淵的巨潮，對範圍內所有目標造成毀滅級魔法傷害。", TargetSpec.AREA, 145, ("damage:water:magic",)),
        ),
        *_elemental_spells(
            "earth",
            # 土 — 學徒
            ("stone_shard", "石礫術", "凝聚土之魔力擲出石礫，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 12, ("damage:earth:magic",)),
            # 土 — 術師
            ("stone_armor", "岩甲術", "以岩石覆蓋目標形成岩甲，提升防禦。", TargetSpec.SINGLE, 24, ("buff_apply:earth_stone_armor",)),
            ("dust_veil", "沙塵術", "捲起漫天沙塵，降低範圍內所有目標的命中。", TargetSpec.AREA, 22, ("buff_apply:earth_dust_veil",)),
            # 土 — 大師
            ("earth_bind", "地縛術", "使大地隆起束縛目標，限制範圍內所有目標的行動。", TargetSpec.AREA, 42, ("buff_apply:earth_root",)),
            ("rockslide", "岩壁崩落", "使岩壁崩落碾壓目標，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 48, ("damage:earth:magic",)),
            # 土 — 賢者
            ("earthquake", "地震術", "撼動大地引發地震，對範圍內所有目標造成極高魔法傷害。", TargetSpec.AREA, 90, ("damage:earth:magic",)),
            ("earthen_ward", "大地庇護", "以大地之力庇護目標，提升範圍內所有目標的防禦。", TargetSpec.AREA, 75, ("buff_apply:earth_ward",)),
            # 土 — 主宰
            ("mountain_collapse", "山嶽崩落", "令山嶽崩落壓垮一切，對範圍內所有目標造成毀滅級魔法傷害。", TargetSpec.AREA, 150, ("damage:earth:magic",)),
            ("earths_judgment", "大地審判", "喚起大地審判之力，對單一目標造成處決級魔法傷害。", TargetSpec.SINGLE, 130, ("damage:earth:magic",)),
        ),
        # 土 — 學徒
        # hardened_skin is inherently self-only (`self_buff_apply`), so it
        # declares SELF_ONLY — the `_elemental_spells` builder fixes ANY, so
        # this single entry is written out individually per the skill-registry
        # spec's self-only constraint.
        _skill(
            "hardened_skin",
            "硬化肌膚",
            "使自身肌膚硬化如岩，提升防禦。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"mp": 10},
            element="earth",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:earth_hardened_skin"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
        ),
        *_elemental_spells(
            "wind",
            # 風 — 學徒
            ("wind_blade", "風刃術", "颳起銳利風刃，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 14, ("damage:wind:magic",)),
            # 風 — 術師
            ("tornado_blade", "龍捲風刃", "捲起龍捲風刃，對單一目標造成高額魔法傷害。", TargetSpec.SINGLE, 26, ("damage:wind:magic",)),
            # 風 — 大師
            ("storm_domain", "暴風領域", "展開暴風領域，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 50, ("damage:wind:magic",)),
            ("gale_dance_strike", "疾風刃舞", "以疾風之勢舞動刃擊，對單一目標造成多段魔法傷害。", TargetSpec.SINGLE, 40, ("damage:wind:magic",)),
            # 風 — 賢者
            ("heavens_wrath_storm", "天譴風暴", "喚起天譴風暴，對範圍內所有目標造成極高魔法傷害。", TargetSpec.AREA, 90, ("damage:wind:magic",)),
            ("haste_domain", "神速領域", "展開神速領域，提升範圍內所有目標的速度。", TargetSpec.AREA, 70, ("buff_apply:wind_haste_domain",)),
            # 風 — 主宰
            ("vacuum_severance", "真空斬滅", "斬出真空之刃，對單一目標造成處決級魔法傷害。", TargetSpec.SINGLE, 130, ("damage:wind:magic",)),
            ("sky_tempest", "蒼穹暴風", "召喚蒼穹暴風，對範圍內所有目標造成毀滅級魔法傷害。", TargetSpec.AREA, 150, ("damage:wind:magic",)),
        ),
        # 風 — 學徒
        # gale_step is inherently self-only (`self_buff_apply`), so it declares
        # SELF_ONLY — the `_elemental_spells` builder fixes ANY, so this single
        # entry is written out individually per the skill-registry spec's
        # self-only constraint.
        _skill(
            "gale_step",
            "疾風術",
            "以疾風強化自身，提升速度。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"mp": 10},
            element="wind",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:wind_haste"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
        ),
        _skill(
            "flight",
            "飛行術",
            "操控風元素飛行，可前往遠處的場合。",
            SkillKind.PASSIVE,
            TargetSpec.SELF,
            cost={"mp": 22},
            usable_out_of_combat=True,
            element="wind",
            effects=["movement:flight"],
            category=SkillCategory.MOVEMENT,
        ),
        *_elemental_spells(
            "lightning",
            # 雷 — 學徒
            ("spark_shock", "電擊術", "凝聚雷之魔力電擊，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 13, ("damage:lightning:magic",)),
            # 雷 — 術師
            ("chain_lightning", "雷鎖術", "釋放連鎖閃電，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 27, ("damage:lightning:magic",)),
            ("paralyzing_bolt", "麻痺電擊", "射出麻痺電擊，對單一目標造成魔法傷害並使其麻痺。", TargetSpec.SINGLE, 24, ("damage:lightning:magic", "buff_apply:paralysis")),
            # 雷 — 大師
            ("thunder_combo", "雷霆連擊", "以雷霆之勢連續攻擊，對單一目標造成多段魔法傷害。", TargetSpec.SINGLE, 46, ("damage:lightning:magic",)),
            ("lightning_strike", "落雷術", "召喚落雷，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 50, ("damage:lightning:magic",)),
            # 雷 — 賢者
            ("heavens_thunder", "天雷降臨", "召喚天雷降臨，對範圍內所有目標造成極高魔法傷害。", TargetSpec.AREA, 92, ("damage:lightning:magic",)),
            # 雷 — 主宰
            ("judgement_thunder", "審判雷霆", "喚起審判雷霆，對單一目標造成處決級魔法傷害。", TargetSpec.SINGLE, 135, ("damage:lightning:magic",)),
            ("divine_lightning_slaughter", "神雷滅殺", "召喚神雷滅殺一切，對範圍內所有目標造成毀滅級魔法傷害。", TargetSpec.AREA, 155, ("damage:lightning:magic",)),
        ),
        # 雷 — 學徒
        # static_ward and thunder_gods_haste are inherently self-only
        # (`self_buff_apply`), so they declare SELF_ONLY — the
        # `_elemental_spells` builder fixes ANY, so these entries are written
        # out individually per the skill-registry spec's self-only constraint.
        _skill(
            "static_ward",
            "靜電護體",
            "以靜電護體，隨時反擊近身之敵。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"mp": 10},
            element="lightning",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:lightning_static_ward"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
        ),
        # 雷 — 賢者
        _skill(
            "thunder_gods_haste",
            "雷神之速",
            "獲得雷神之速，追加行動機會。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"mp": 68},
            element="lightning",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:lightning_extra_action"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
        ),
        *_elemental_spells(
            "ice",
            # 冰 — 學徒
            ("ice_shard", "冰錐術", "凝聚冰之魔力化為冰錐，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 13, ("damage:ice:magic",)),
            ("frost_breath", "凍結之息", "吐出凍結之息，降低單一目標的速度。", TargetSpec.SINGLE, 11, ("buff_apply:ice_slow",)),
            # 冰 — 術師
            ("ice_wall", "冰牆術", "築起冰牆，提升目標的防禦。", TargetSpec.SINGLE, 25, ("buff_apply:ice_wall",)),
            ("frost_arrow_rain", "冷凍箭雨", "降下冷凍箭雨，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 28, ("damage:ice:magic",)),
            # 冰 — 大師
            ("permafrost_domain", "永凍領域", "展開永凍領域，凍結範圍內所有目標。", TargetSpec.AREA, 48, ("buff_apply:ice_freeze",)),
            ("ice_prison", "冰封監牢", "以寒冰封鎖目標，定住其行動。", TargetSpec.SINGLE, 44, ("buff_apply:ice_prison",)),
            # 冰 — 賢者
            ("blizzard", "暴風雪", "喚起暴風雪，對範圍內所有目標造成極高魔法傷害。", TargetSpec.AREA, 88, ("damage:ice:magic",)),
            ("absolute_tundra", "絕對凍土", "將大地凍結為絕對凍土，對範圍內所有目標造成魔法傷害並使其凍結。", TargetSpec.AREA, 82, ("damage:ice:magic", "buff_apply:ice_freeze")),
            # 冰 — 主宰
            ("absolute_zero", "絕對零度", "釋放絕對零度，對單一目標造成處決級魔法傷害並使其凍結。", TargetSpec.SINGLE, 140, ("damage:ice:magic", "buff_apply:ice_freeze")),
            ("eternal_ice_field", "永夜冰原", "展開永夜的冰原，對範圍內所有目標造成毀滅級魔法傷害並使其凍結。", TargetSpec.AREA, 158, ("damage:ice:magic", "buff_apply:ice_freeze")),
        ),
        *_elemental_spells(
            "light",
            # 光 — 學徒
            ("heal", "治癒術", "以光之魔力治癒，恢復單一目標的生命力。", TargetSpec.SINGLE, 12, ("heal:single",)),
            ("light_arrow", "光箭術", "射出光之箭矢，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 14, ("damage:light:magic",)),
            # 光 — 術師
            ("purify", "淨化術", "以淨化之光，解除單一目標的異常狀態。", TargetSpec.SINGLE, 22, ("cleanse:status",)),
            ("mass_heal", "群體治癒", "施展群體治癒，恢復範圍內所有目標的生命力。", TargetSpec.AREA, 30, ("heal:area",)),
            # 光 — 大師
            ("advanced_heal", "高級治癒", "施展高級治癒，大量恢復單一目標的生命力。", TargetSpec.SINGLE, 46, ("heal:single",)),
            ("holy_shield", "聖盾術", "以神聖之力形成聖盾，提升單一目標的防禦。", TargetSpec.SINGLE, 40, ("buff_apply:light_holy_shield",)),
            # 光 — 賢者
            ("holy_radiance", "神聖光輝", "綻放神聖光輝，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 90, ("damage:light:magic",)),
            ("revival_light", "復甦之光", "綻放復甦之光，大量恢復瀕危目標的生命力。", TargetSpec.SINGLE, 82, ("heal:single",)),
            # 光 — 主宰
            ("goddess_blessing", "女神降福", "獲得女神的祝福，大量恢復範圍內所有目標的生命力並強化防禦。", TargetSpec.AREA, 145, ("heal:area", "buff_apply:light_blessing")),
            ("heavens_judgment_light", "天啟聖裁", "喚起天啟聖裁，對單一目標造成毀滅級魔法傷害。", TargetSpec.SINGLE, 135, ("damage:light:magic",)),
        ),
        *_elemental_spells(
            "dark",
            # 暗 — 學徒
            ("shadow_bolt", "暗影箭", "射出暗影之箭，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 14, ("damage:dark:magic",)),
            ("weaken", "衰弱術", "施展衰弱術，降低單一目標的攻擊。", TargetSpec.SINGLE, 11, ("buff_apply:dark_atk_down",)),
            # 暗 — 術師
            ("curse", "詛咒術", "施展詛咒，削弱單一目標的多項能力。", TargetSpec.SINGLE, 26, ("buff_apply:dark_curse",)),
            ("dark_burst", "闇裂術", "釋放闇之爆裂，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 29, ("damage:dark:magic",)),
            # 暗 — 大師
            ("dark_corrosion_domain", "闇蝕領域", "展開闇蝕領域，對範圍內所有目標造成魔法傷害並使其腐蝕。", TargetSpec.AREA, 47, ("damage:dark:magic", "buff_apply:dark_corrosion")),
            ("shadow_torment", "暗影凌遲", "以暗影凌遲目標，造成高額魔法傷害並使其腐蝕。", TargetSpec.SINGLE, 41, ("damage:dark:magic", "buff_apply:dark_corrosion")),
            # 暗 — 賢者
            ("abyss_devour", "深淵吞噬", "召喚深淵吞噬目標，對單一目標造成處決級魔法傷害。", TargetSpec.SINGLE, 85, ("damage:dark:magic",)),
            ("dark_dominion", "黑暗支配", "展開黑暗支配，使範圍內所有目標陷入恐懼。", TargetSpec.AREA, 72, ("buff_apply:fear",)),
            # 暗 — 主宰
            ("void_annihilation", "終焉黑洞", "召喚終焉黑洞，對範圍內所有目標造成毀滅級魔法傷害。", TargetSpec.AREA, 155, ("damage:dark:magic",)),
            ("netherworld_judgment", "冥府審判", "喚起冥府審判，對單一目標造成處決級魔法傷害。", TargetSpec.SINGLE, 135, ("damage:dark:magic",)),
        ),
        _skill(
            "dual_wield_style",
            "雙持劍術",
            "同時揮舞兩把武器進行戰鬥的架式。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["weapon_style:dual_wield"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _skill(
            "dual_blade_mastery",
            "雙刀流·宗師級",
            "以宗師級的雙刀連擊，對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 30},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _skill(
            "light_sword_style",
            "光劍架式",
            "以光之劍的架式對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 6},
            element="light",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:light:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _skill(
            "shadow_slash",
            "影斬",
            "潛入闇影後對單一目標斬出一記物理攻擊。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 18},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _skill(
            "flash_step",
            "瞬步",
            "以高速步伐瞬間移動，可前往較近的場合。",
            SkillKind.PASSIVE,
            TargetSpec.SELF,
            cost={"sp": 12},
            usable_out_of_combat=True,
            effects=["movement:flash_step"],
            category=SkillCategory.MOVEMENT,
        ),
        _skill(
            "status_disguise",
            "神之秘法：狀態偽裝",
            "以神之秘法偽裝自身的外貌與部分能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            effects=["set_disguise"],
            category=SkillCategory.UTILITY,
        ),
        _skill(
            "concentration",
            "集中",
            "凝聚精神，暫時提升自身的專注與準確度。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            cost={"mp": 5},
            effects=["self_buff_apply:focus"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "dominion_art",
            "統御術",
            "授予目標一部分自身技能的效果。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            effects=["confer_skill_partial"],
            category=SkillCategory.UTILITY,
        ),
        _skill(
            "defense_instinct",
            "防禦直覺",
            "被動強化自身的防禦能力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:defense_small"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "blade_art_mastery",
            "劍術精通",
            "被動提昇劍術與刀術相關技能的效果。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:blade_arts"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "extreme_endurance",
            "極限耐力",
            "被動強化自身的耐力上限。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:endurance_extreme"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "magic_circle_comprehension",
            "魔法陣理解",
            "被動提昇對魔法陣的理解與運用。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:magic_circle_comprehension"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "precise_mana_control",
            "精準魔力控制",
            "被動強化對魔力的精準控制。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:mana_precision"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "retainer_martial_training",
            "隨從武藝訓練",
            "被動提昇隨從角色的武藝水準。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:retainer_training"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "guardian_instinct",
            "護主本能",
            "被動強化守護主人、忠誠護衛的本能。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:guardian_instinct"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "elf_longevity",
            "精靈長壽",
            "被動延長生命週期，是精靈種族的特質。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_trait:elf_longevity"],
            category=SkillCategory.INNATE_GIFT,
        ),
        _skill(
            "reincarnation_boon_elosia",
            "轉生祝福·伊洛希雅",
            "轉生帶來的祝福，被動加速魔力成長。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["growth_rate:practice:100"],
            category=SkillCategory.INNATE_GIFT,
        ),
        _skill(
            "reincarnation_boon_yuka",
            "轉生祝福·悠花",
            "轉生帶來的祝福，被動強化戰鬥預感。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["combat_prediction:武感"],
            category=SkillCategory.INNATE_GIFT,
        ),
        _skill(
            "reincarnation_boon_yuna",
            "轉生祝福·悠奈",
            "轉生帶來的祝福，被動精通性魔法的掌握。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["sexual_magic_mastery"],
            category=SkillCategory.SEXUAL_ACT,
            group="精通",
        ),
        _skill(
            "divine_sexual_mastery",
            "性魔法主宰",
            "以神性掌握性魔法精髓的至高境界，被動證明對性魔法領域的絕對理解。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            requires_divine_arts=True,
            effects=["sexual_magic_mastery"],
            category=SkillCategory.SEXUAL_ACT,
            group="精通",
        ),
        _skill(
            "divine_sexual_arts",
            "神之秘法：性愛系統",
            "以神之秘法引導的性愛技法，直接刺激目標的感官與慾望。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["sexual_event:stimulus_applied"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
        ),
        _skill(
            "divine_time_dilation",
            "神之秘法：時間加速",
            "以神性加速或減緩時間流動的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:時間加速"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "divine_space_distortion",
            "神之秘法：空間扭曲",
            "以神性扭曲空間，使存在與景物移位重組的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:空間扭曲"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "divine_matter_transmutation",
            "神之秘法：物質轉換",
            "以神性改變物質本質，將萬物轉化為其他形態的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:物質轉換"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "divine_life_extension",
            "神之秘法：生命延續",
            "以神性延續生命與壽命的秘法，據說能超越種族的極限。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:生命延續"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
    )
}
