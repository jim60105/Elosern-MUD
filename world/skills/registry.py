"""Skill definitions from design section 5.2 and ``skills-equipment``.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. Every ``effects`` string is
parsed into a typed dataclass by ``world.skills.effects.parse_effect`` at
construction; see that module for the recognized effect-ID conventions.

``SkillPrerequisite`` declares the skill-lineage DAG (use-driven-progression
design §9): an edge ``consumer -> (skill_key, min_proficiency)`` gating USE
(never ownership). ``validate_prerequisite_graph`` runs fail-closed at
registry load and caches the reverse-edge map the tip-cap derivation reads.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import (
    ActorSexualEventEffect,
    ClampShameEffect,
    ClimaxExtensionStageEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DamageEffect,
    DamagePolicy,
    DivinePleasureMaxEffect,
    EffectAudience,
    EffectPolicy,
    GaugeTransferEffect,
    GaugeTransferPolicy,
    HealEffect,
    InteractionPolicy,
    MarkSubmissionEffect,
    PleasurePeakEffect,
    RestorePurityEffect,
    SaturateSensitivityEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualDrainEffect,
    StateMagnitude,
    StateMagnitudeSubject,
    StimulusEffect,
    TargetSexualEventEffect,
    parse_effect,
)
from world.skills.cast_conditions import CastCondition, CastConditionSubject


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
    DIVINE_MYSTERY = "divine_mystery"
    UTILITY = "utility"
    SEXUAL_ACT = "sexual_act"


# Presentation metadata bounds shared by every immutable skill definition.
LABEL_MAX = 128
DESCRIPTION_MAX = 512


@dataclass(frozen=True, slots=True)
class SkillPrerequisite:
    """One skill-lineage edge: a consumer requires ``min_proficiency`` in ``skill_key``.

    The threshold is a whole proficiency level and must be >= 1: a 0-level
    requirement would gate nothing while still rendering as a visible edge,
    so the constructor rejects it (fail closed at construction, matching the
    registry's other invariant checks).
    """

    skill_key: str
    min_proficiency: int

    def __post_init__(self) -> None:
        if not isinstance(self.skill_key, str) or not self.skill_key.strip():
            raise ValueError(
                "SkillPrerequisite.skill_key must be a non-empty string"
            )
        if isinstance(self.min_proficiency, bool) or not isinstance(
            self.min_proficiency, int
        ):
            raise ValueError(
                f"SkillPrerequisite on {self.skill_key!r}: min_proficiency "
                f"must be an int, got {self.min_proficiency!r}"
            )
        if self.min_proficiency < 1:
            raise ValueError(
                f"SkillPrerequisite on {self.skill_key!r}: min_proficiency "
                f"must be >= 1, got {self.min_proficiency}"
            )


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
    effect_policies: tuple[EffectPolicy, ...] = ()
    parsed_effects: tuple = ()
    prerequisites: tuple["SkillPrerequisite", ...] = ()
    cast_conditions: tuple[CastCondition, ...] = ()
    interaction: InteractionPolicy | None = None

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
        if isinstance(self.prerequisites, (str, bytes)) or not isinstance(
            self.prerequisites, tuple
        ):
            raise ValueError(
                f"skill {self.key!r} prerequisites must be a tuple of "
                "SkillPrerequisite"
            )
        for prereq in self.prerequisites:
            if not isinstance(prereq, SkillPrerequisite):
                raise ValueError(
                    f"skill {self.key!r} prerequisite {prereq!r} is not a "
                    "SkillPrerequisite"
                )
        if isinstance(self.cast_conditions, (str, bytes)) or not isinstance(
            self.cast_conditions, tuple
        ):
            raise ValueError(
                f"skill {self.key!r} cast_conditions must be a tuple of CastCondition"
            )
        for cond in self.cast_conditions:
            if not isinstance(cond, CastCondition):
                raise ValueError(
                    f"skill {self.key!r} cast_condition {cond!r} is not a CastCondition"
                )

        # The declared type is Element | None: normalize (and validate) a raw
        # string on EVERY constructor path, so direct SkillDef(...) authors
        # (flee, test fixtures) cannot leave a str where consumers read
        # ``skill.element.key``.
        if isinstance(self.element, str):
            resolved = ELEMENT_REGISTRY.get(self.element)
            if resolved is None:
                raise ValueError(
                    f"skill {self.key!r} declares unknown element "
                    f"{self.element!r}"
                )
            object.__setattr__(self, "element", resolved)
        elif self.element is not None and not isinstance(self.element, Element):
            raise ValueError(
                f"skill {self.key!r} element must be an Element, a string key, "
                f"or None, got {type(self.element).__name__}"
            )
        object.__setattr__(self, "cost", _FrozenDict(self.cost))
        object.__setattr__(self, "effects", _FrozenList(self.effects))
        object.__setattr__(
            self,
            "parsed_effects",
            tuple(parse_effect(effect_id) for effect_id in self.effects),
        )
        # One-directional by design (elementless-damage-effect D3): an
        # element-bearing damage effect on a skill declaring no element is
        # pre-existing content and stays legal; only the new contradiction
        # (a declared element alongside an elementless damage effect) fails.
        if self.element is not None:
            for effect_id, parsed in zip(self.effects, self.parsed_effects):
                if isinstance(parsed, DamageEffect) and parsed.element is None:
                    raise ValueError(
                        f"skill {self.key!r} declares element {self.element.key!r} "
                        f"together with an elementless damage effect {effect_id!r}; "
                        "a skill cannot declare both"
                    )
        self._validate_effect_policies()
        # Interaction derivation runs only AFTER effect_policies validation:
        # a raw (non-EffectPolicy) declaration is rejected there with the
        # registry error, never iterated here as policy rows.
        if self.interaction is None:
            for p in self.effect_policies:
                if p.interaction is not None:
                    object.__setattr__(self, "interaction", p.interaction)
                    break
        elif not isinstance(self.interaction, InteractionPolicy):
            raise ValueError(
                f"skill {self.key!r} interaction must be an InteractionPolicy or None, got {self.interaction!r}"
            )
        self._validate_heal_shape()

    def _validate_effect_policies(self) -> None:
        """Enforce cardinality, immutability, and supported-effect kinds on policies.

        An omitted or empty-tuple declaration normalizes to identity policies
        of the same length as ``effects``. Any other input must be a tuple of
        ``EffectPolicy`` instances matching the effect count exactly (an
        all-default tuple re-normalizes if ``effects`` length changed via
        ``replace()``), and only supported effect kinds (damage, healing,
        and the two conferral classes) may declare a non-identity
        coefficient — which doubles as the conferral scale.
        """
        if self.effect_policies is None or (
            isinstance(self.effect_policies, tuple) and len(self.effect_policies) == 0
        ):
            object.__setattr__(
                self,
                "effect_policies",
                tuple(EffectPolicy() for _ in self.effects),
            )
            return

        if isinstance(self.effect_policies, (str, bytes)) or not isinstance(
            self.effect_policies, tuple
        ):
            raise ValueError(
                f"skill {self.key!r} effect_policies must be a tuple of EffectPolicy"
            )
        if len(self.effect_policies) != len(self.effects):
            if all(p == EffectPolicy() for p in self.effect_policies):
                object.__setattr__(
                    self,
                    "effect_policies",
                    tuple(EffectPolicy() for _ in self.effects),
                )
                return
            raise ValueError(
                f"skill {self.key!r} effect_policies length ({len(self.effect_policies)}) "
                f"must match effects length ({len(self.effects)})"
            )
        for policy in self.effect_policies:
            if not isinstance(policy, EffectPolicy):
                raise ValueError(
                    f"skill {self.key!r} effect_policies item {policy!r} is not an EffectPolicy"
                )
            if (
                self.target_spec is TargetSpec.NONE
                and policy.audience in (EffectAudience.ALLIES, EffectAudience.ENEMIES)
            ):
                raise ValueError(
                    f"skill {self.key!r} target_spec is NONE and cannot declare {policy.audience} audience"
                )
        for policy, parsed, effect_id in zip(
            self.effect_policies, self.parsed_effects, self.effects
        ):
            if policy.coefficient != 1.0 and not (
                isinstance(
                    parsed,
                    (
                        DamageEffect,
                        HealEffect,
                        ConferralEffect,
                        ConferGrowthRateEffect,
                    ),
                )
                or (isinstance(parsed, SelfHealEffect) and parsed.basis == "stat")
            ):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} does not support "
                    f"potency coefficient {policy.coefficient}"
                )
            if policy.damage is not None and not isinstance(parsed, DamageEffect):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} is not a DamageEffect and "
                    f"cannot declare a DamagePolicy"
                )
            if (
                isinstance(
                    parsed,
                    (SelfHealEffect, ActorSexualEventEffect, SelfBuffApplyEffect),
                )
                and policy.audience in (EffectAudience.ALLIES, EffectAudience.ENEMIES)
            ):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} is inherently actor-bound and "
                    f"cannot declare {policy.audience} audience"
                )
            if (
                isinstance(
                    parsed,
                    (
                        TargetSexualEventEffect,
                        DivinePleasureMaxEffect,
                        ClimaxExtensionStageEffect,
                        SexualDrainEffect,
                        SaturateSensitivityEffect,
                        ClampShameEffect,
                        MarkSubmissionEffect,
                        RestorePurityEffect,
                    ),
                )
                and policy.audience is EffectAudience.SELF
            ):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} is inherently target-only and "
                    f"cannot declare SELF audience"
                )
            if (
                self.target_spec is TargetSpec.SELF
                and policy.audience is EffectAudience.ENEMIES
            ):
                raise ValueError(
                    f"skill {self.key!r} target_spec is SELF and cannot declare ENEMIES audience"
                )
            if isinstance(parsed, StimulusEffect):
                if policy.damage is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is a StimulusEffect and cannot declare DamagePolicy"
                    )
                if policy.coefficient != 1.0:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support potency coefficient {policy.coefficient}"
                    )
                if parsed.recipient == "actor" and policy.audience in (EffectAudience.ALLIES, EffectAudience.ENEMIES):
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is inherently actor-bound and cannot declare {policy.audience} audience"
                    )
                if parsed.recipient == "target" and policy.audience is EffectAudience.SELF:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is inherently target-only and cannot declare SELF audience"
                    )
            if policy.stimulus_bonus is not None and not isinstance(parsed, StimulusEffect):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} is not a StimulusEffect and cannot declare stimulus_bonus"
                )
            if isinstance(parsed, PleasurePeakEffect):
                if policy.damage is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is a PleasurePeakEffect and cannot declare DamagePolicy"
                    )
                if policy.stimulus_bonus is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is a PleasurePeakEffect and cannot declare stimulus_bonus"
                    )
                if policy.magnitude is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support state magnitude"
                    )
                if policy.coefficient != 1.0:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support potency coefficient {policy.coefficient}"
                    )
            if policy.magnitude is not None:
                if not isinstance(parsed, (DamageEffect, HealEffect, SelfHealEffect)):
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support state magnitude"
                    )
                if (
                    policy.magnitude.subject == StateMagnitudeSubject.TARGET
                    and self.target_spec not in (TargetSpec.SINGLE, TargetSpec.SELF)
                ):
                    raise ValueError(
                        f"skill {self.key!r} TARGET-subject magnitude requires SINGLE or SELF target_spec"
                    )
            if isinstance(parsed, GaugeTransferEffect):
                if policy.coefficient != 1.0:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support "
                        f"potency coefficient {policy.coefficient}"
                    )
                if policy.damage is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is a GaugeTransferEffect and cannot declare DamagePolicy"
                    )
                if policy.magnitude is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} does not support state magnitude"
                    )
                if policy.stimulus_bonus is not None:
                    raise ValueError(
                        f"skill {self.key!r} effect {effect_id!r} is a GaugeTransferEffect and cannot declare stimulus_bonus"
                    )
                if policy.transfer is not None:
                    if parsed.direction == "drain" and policy.transfer.restore_bonus_per_stack:
                        raise ValueError(
                            f"skill {self.key!r} effect {effect_id!r} is a drain and cannot declare restore_bonus_per_stack"
                        )
            if policy.transfer is not None and not isinstance(parsed, GaugeTransferEffect):
                raise ValueError(
                    f"skill {self.key!r} effect {effect_id!r} is not a GaugeTransferEffect and cannot declare GaugeTransferPolicy"
                )

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
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    effect_policies: tuple[EffectPolicy, ...] | None = None,
    cast_conditions: tuple[CastCondition, ...] = (),
    interaction: InteractionPolicy | None = None,
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
        prerequisites=prerequisites,
        effect_policies=() if effect_policies is None else tuple(effect_policies),
        cast_conditions=tuple(cast_conditions),
        interaction=interaction,
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
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    category: SkillCategory,
    group: str | None = None,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    effect_policies: tuple[EffectPolicy, ...] | None = None,
    cast_conditions: tuple[CastCondition, ...] = (),
    interaction: InteractionPolicy | None = None,
) -> SkillDef:
    """Build one ACTIVE elemental spell — the design doc §4.4 catalog shape.

    Every catalog spell is an ACTIVE skill at an integer MP cost. By default,
    spells are freely targetable among enemies and allies (FactionConstraint.ANY);
    self-targeted buffs (e.g. water_shield) declare FactionConstraint.SELF_ONLY.
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
        faction_constraint=faction_constraint,
        category=category,
        group=group,
        prerequisites=prerequisites,
        effect_policies=effect_policies,
        cast_conditions=cast_conditions,
        interaction=interaction,
    )


def _elemental_spells(
    element: str,
    *spells: tuple[Any, ...],
) -> tuple[SkillDef, ...]:
    """Build one element's full ACTIVE spell set (design doc §4.4).

    Each row is ``(key, label, description, target_spec, mp, effects)``, with
    an optional seventh ``prerequisites`` entry carrying this skill's lineage
    edges (``()`` when absent). The element is written once for the whole set. A spell's tier is
    deliberately NOT a stored field: it stays derivable from the set's
    grouping and each row's MP cost band (``spell_tier_for``), per the
    skill-registry spec.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r} for elemental spell set")

    def _row(row: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(row) == 6:
            return (*row, ())
        if len(row) == 7:
            return row
        raise ValueError(
            "elemental spell rows carry 6 or 7 fields, got "
            f"{len(row)}: {row[0] if row else '?'}"
        )

    return tuple(
        _spell(
            key,
            label,
            description,
            target_spec,
            usable_out_of_combat=True,
            mp=mp,
            element=element,
            effects=effects,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group=element,
            prerequisites=prerequisites,
        )
        for key, label, description, target_spec, mp, effects, prerequisites in (
            _row(row) for row in spells
        )
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
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _body_multiplier("body_enhancement", "身體強化", 100),
        _body_multiplier("body_enhancement_extreme", "身體超強化", 1000),
        _body_multiplier("body_enhancement_basic", "基礎身體強化", 1.2),
        _skill(
            "fire_mastery",
            "火焰精通",
            "被動提昇火焰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
            element="ice",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
        ),
        # 火 — 學徒（根與基礎）
        _spell(
            "fire_arrow",
            "火焰箭",
            "射出火焰凝聚的箭矢，以低耗能對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=10,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        _spell(
            "fire_ball",
            "火球術",
            "凝聚火焰魔力，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=14,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("fire_arrow", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 火 — 術師（三分支點）
        _spell(
            "scorching_wave",
            "灼熱波動",
            "釋放灼熱的波動，對單一目標造成魔法傷害並使其灼燒。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="fire",
            effects=("damage:fire:magic", "buff_apply:fire_scorch"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("fire_ball", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
            ),
        ),
        _spell(
            "firestorm",
            "火焰風暴",
            "召喚覆蓋範圍的火焰風暴，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=30,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("scorching_wave", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 火 — 大師（單體分支終點）
        _spell(
            "flame_shroud",
            "烈焰纏繞",
            "以烈焰纏繞單一目標，造成高額魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=42,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("scorching_wave", 3),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 火 — 術師（反灼護甲・分支終點）
        _spell(
            "scorching_armor",
            "灼熱裝甲",
            "覆上灼熱裝甲，受擊時攻擊者被點燃陷入灼燒。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=20,
            element="fire",
            effects=("self_buff_apply:fire_scorching_armor",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("scorching_wave", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 火 — 大師（範圍地形）
        _spell(
            "lava_burst",
            "熔岩術",
            "使地面迸裂噴出熔岩，對範圍內所有目標造成魔法傷害並附加熔岩地形。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=52,
            element="fire",
            effects=("damage:fire:magic", "buff_apply:fire_lava"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("firestorm", 5),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
            ),
        ),
        # 火 — 賢者（單體極限）
        _spell(
            "hellfire",
            "煉獄之火",
            "召喚煉獄之火，對單一目標造成極高魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=78,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("firestorm", 5),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 火 — 賢者（範圍巨幅）
        _spell(
            "dragon_flame",
            "龍炎術",
            "喚起龍之吐息，對範圍內所有目標造成高額魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=95,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("lava_burst", 8),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 火 — 主宰（處決級）
        _spell(
            "final_blaze",
            "焚世之焰",
            "召喚足以焚盡世界的焰流，無視防禦對單一目標造成處決級魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("hellfire", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 火 — 主宰（燃身溢位）
        _spell(
            "sacrificial_flame",
            "燔祭焰",
            "獻上自身體能為祭，召喚燔祭之焰對範圍內所有目標造成極高魔法傷害，自身承受灼燒。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="fire",
            effects=("damage:fire:magic", "self_buff_apply:fire_sacrifice_burn"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(SkillPrerequisite("dragon_flame", 8),),
            effect_policies=(
                EffectPolicy(coefficient=3.4),
                EffectPolicy(),
            ),
        ),
        # 火 — 神格（兩線匯合・雙向燃身）
        _spell(
            "crimson_apotheosis",
            "紅蓮神格",
            "化身紅蓮，以自身承受灼燒為代價對範圍內所有敵人造成毀滅級魔法傷害，並使敵方全體陷入紅蓮業火。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=210,
            element="fire",
            effects=(
                "damage:fire:magic",
                "buff_apply:fire_crimson_burn",
                "self_buff_apply:fire_crimson_self",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(
                SkillPrerequisite("sacrificial_flame", 10),
                SkillPrerequisite("final_blaze", 10),
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=4.4),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(),
            ),
        ),
        # 水 — 學徒（潮汐路線）
        _spell(
            "tide_pull",
            "潮引術",
            "引動魔力潮汐，命中使目標魔力流失並回收其中一半至施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="water",
            effects=("gauge_transfer:mp:drain:fixed:5",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            effect_policies=(
                EffectPolicy(
                    transfer=GaugeTransferPolicy(caster_recovery_share=0.5),
                ),
            ),
        ),
        # 水 — 術師（潮汐路線）
        _spell(
            "ebbing_blight",
            "潮退侵蝕",
            "喚起退潮之蝕，對單一目標造成魔法傷害並附加潮退，持續造成魔力流失。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="water",
            effects=("damage:water:magic", "buff_apply:ebbing"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("tide_pull", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.0),
                EffectPolicy(),
            ),
        ),
        _spell(
            "water_shield",
            "水膜護身",
            "凝聚水膜護身，受擊時以魔力代扣傷害。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=22,
            element="water",
            effects=("self_buff_apply:water_film",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ebbing_blight", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 水 — 大師（潮汐路線）
        _spell(
            "ring_of_reflux",
            "回流之環",
            "引導魔力回流，恢復單一目標魔力，並依施法者身上的潮退標記獲得額外加值。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=42,
            element="water",
            effects=("gauge_transfer:mp:restore:fixed:40",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ebbing_blight", 3),),
            effect_policies=(
                EffectPolicy(
                    transfer=GaugeTransferPolicy(
                        restore_bonus_per_stack=(
                            ("ebbing", 10),
                            ("ebbing_deep", 10),
                            ("ebbing_maelstrom", 10),
                        ),
                    ),
                ),
            ),
        ),
        # 水 — 賢者（潮汐路線）
        _spell(
            "drowned_surging",
            "溺潮",
            "引發溺滅魔潮，使目標魔力加速流失，魔力歸零時陷入窒息；對魔力上限為零者改為造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=78,
            element="water",
            effects=("buff_apply:ebbing_maelstrom", "damage:water:magic"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ring_of_reflux", 5),),
            effect_policies=(
                EffectPolicy(),
                EffectPolicy(audience_condition="mp_max_zero"),
            ),
        ),
        # 水 — 主宰（潮汐路線）
        _spell(
            "sigil_of_the_barren_sea",
            "枯海之印",
            "施加枯海之印，對單一目標造成處決級魔法傷害，移除全部魔力並封鎖其恢復。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="water",
            effects=(
                "damage:water:magic",
                "gauge_transfer:mp:drain:all",
                "buff_apply:mp_regen_lock",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("drowned_surging", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 水 — 賢者（潮汐路線・範圍友方）
        _spell(
            "abyssal_surge",
            "深淵潮汛",
            "引動深淵魔潮，恢復我方全體魔力並附著回流狀態。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=82,
            element="water",
            effects=("gauge_transfer:mp:restore:fixed:25", "buff_apply:mana_reflux"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ring_of_reflux", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ALLIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
        # 水 — 學徒（深海路線）
        _spell(
            "water_bolt",
            "水箭術",
            "凝聚水之魔力化為箭矢，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 水 — 術師（深海路線）
        _spell(
            "deep_current_spike",
            "深流刺",
            "凝聚深層暗流化為尖刺，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("water_bolt", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 水 — 大師（深海路線）
        _spell(
            "abyssal_whirlpool",
            "深海漩渦",
            "召喚深海漩渦，對範圍內所有目標造成魔法傷害、附加潮退並束縛其行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="water",
            effects=(
                "damage:water:magic",
                "buff_apply:ebbing_deep",
                "buff_apply:water_bind",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("deep_current_spike", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 水 — 賢者（深海路線）
        _spell(
            "abyssal_maw",
            "深淵巨口",
            "張開如深淵般的巨口，對單一目標造成魔法傷害，並吸取其現有魔力的兩成轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="water",
            effects=("damage:water:magic", "gauge_transfer:mp:drain:fraction:0.2"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("abyssal_whirlpool", 5),),
            effect_policies=(
                EffectPolicy(coefficient=2.8),
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=1.0)),
            ),
        ),
        # 水 — 賢者（深海路線）
        _spell(
            "tsunami",
            "海嘯術",
            "喚起滔天海嘯，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=95,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("abyssal_whirlpool", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 水 — 主宰（深海路線）
        _spell(
            "abyssal_tide",
            "深淵巨潮",
            "召喚深淵巨潮，對範圍內所有目標造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=145,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("tsunami", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 水 — 神格（兩線匯合）
        _spell(
            "abyssal_heart",
            "深海神格",
            "神格之潮降臨，抽乾敵方全體魔力並造成毀滅級魔法傷害，同時將魔力全量歸還我方全體。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=230,
            element="water",
            effects=(
                "damage:water:magic",
                "gauge_transfer:mp:drain:all",
                "gauge_transfer:mp:restore:fixed:25",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(
                SkillPrerequisite("sigil_of_the_barren_sea", 10),
                SkillPrerequisite("abyssal_tide", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
        # 土 — 學徒（地形路線・根）
        _spell(
            "stone_shard",
            "石礫術",
            "凝聚土之魔力擲出石礫，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 土 — 術師（護甲路線）
        _spell(
            "stone_armor",
            "岩甲術",
            "以岩石覆蓋目標形成岩甲，提升防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="earth",
            effects=("buff_apply:earth_stone_armor",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("hardened_skin", 3),),
        ),
        # 土 — 大師（護甲路線・磐石）
        _spell(
            "bedrock_bastion",
            "磐石壁壘",
            "召出磐石壁壘，提升我方全體防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="earth",
            effects=("buff_apply:earth_bedrock",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("stone_armor", 3),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 土 — 賢者（護甲路線・磐石）
        _spell(
            "earthen_ward",
            "大地庇護",
            "以大地之力庇護我方，提升我方全體防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=75,
            element="earth",
            effects=("buff_apply:earth_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("bedrock_bastion", 5),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 土 — 大師（護甲路線・荊棘）
        # thorned_carapace is inherently self-only (`self_buff_apply`); the
        # counter itself is reaction data — earth_carapace is the mount the
        # shipped physical_hit rule's buff_active gate keys off.
        _spell(
            "thorned_carapace",
            "荊棘反甲",
            "覆上荊棘反甲，受到物理攻擊時反彈傷害。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=40,
            element="earth",
            effects=("self_buff_apply:earth_carapace",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            faction_constraint=FactionConstraint.SELF_ONLY,
            prerequisites=(SkillPrerequisite("stone_armor", 3),),
        ),
        # 土 — 術師（地形路線）
        _spell(
            "dust_veil",
            "沙塵術",
            "捲起漫天沙塵，降低範圍內所有目標的命中。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=22,
            element="earth",
            effects=("buff_apply:earth_dust_veil",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("stone_shard", 3),),
        ),
        # 土 — 大師（地形路線・裂縫）
        _spell(
            "ground_fissure",
            "地裂術",
            "地面裂開成縫，留在裂縫上的目標持續承受地形傷害並陷入遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=42,
            element="earth",
            effects=("buff_apply:earth_fissure", "buff_apply:ice_slow"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("dust_veil", 3),),
        ),
        # 土 — 大師（地形路線・崩落）
        _spell(
            "rockslide",
            "岩壁崩落",
            "使岩壁崩落碾壓目標，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("dust_veil", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 土 — 賢者（地形路線・裂縫）
        _spell(
            "earthquake",
            "地震術",
            "撼動大地引發地震，對範圍內所有目標造成魔法傷害，並附加裂縫地形標記與遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="earth",
            effects=(
                "damage:earth:magic",
                "buff_apply:earth_fissure_quake",
                "buff_apply:ice_slow",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("ground_fissure", 5),),
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 土 — 賢者（地形路線・單體）
        _spell(
            "fault_rupture",
            "地脈崩裂",
            "撕裂地脈撼動目標根基，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("rockslide", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 土 — 主宰（地形路線・裂縫）
        _spell(
            "mountain_collapse",
            "山嶽崩落",
            "令山嶽崩落壓垮一切，對範圍內所有目標造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("earthquake", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 土 — 主宰（地形路線・單體）
        # 處決級（無視防禦）+ 裂縫連動：站在任一裂縫標記上觸發一次
        # 1.15 乘算（4.0×1.15=4.6 == 4.0+0.6，D6）；predicate any-match-once
        # 讓三個裂縫 rung 只計一次。
        _spell(
            "earths_judgment",
            "大地審判",
            "喚起大地審判之力，無視防禦對單一目標造成處決級魔法傷害；對站在裂縫上的目標額外加重。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("fault_rupture", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(
                        predicate=(
                            "buff:earth_fissure",
                            "buff:earth_fissure_quake",
                            "buff:earth_fissure_apex",
                        ),
                        attack_multiplier=1.15,
                        unconditional_defense_bypass=True,
                    ),
                ),
            ),
        ),
        # 土 — 神格（兩線匯合）
        # 「覆蓋全場」：頂規裂縫標記與遲緩以 ENEMIES audience 施加於區域
        # 選擇的每個敵方目標（abyssal_heart 先例）。
        _spell(
            "earthen_apotheosis",
            "大地神格",
            "大地甦醒，對範圍內所有敵人造成毀滅級魔法傷害，並召出覆蓋全場的頂規裂縫地形，留在其上者持續承受地形傷害並陷入遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=220,
            element="earth",
            effects=(
                "damage:earth:magic",
                "buff_apply:earth_fissure_apex",
                "buff_apply:ice_slow",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(
                SkillPrerequisite("mountain_collapse", 10),
                SkillPrerequisite("earths_judgment", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
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
            usable_out_of_combat=True,
            cost={"mp": 10},
            element="earth",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:earth_hardened_skin"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
        ),
        # 風 — 學徒（機動路線・根）
        _spell(
            "gale_step",
            "疾風術",
            "以疾風強化自身，提升速度。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=10,
            element="wind",
            effects=("self_buff_apply:gale_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
        ),
        # 風 — 術師（機動路線）
        _spell(
            "gale_chain_step",
            "疾風連步",
            "進一步提升身法流暢度，在移動中積蓄速度。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=20,
            element="wind",
            effects=("self_buff_apply:gale_chain_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_step", 3),),
        ),
        # 風 — 大師（機動路線）
        _spell(
            "afterimage_step",
            "神速殘影",
            "速度突破常規拉出殘影，大幅提升閃避但犧牲攻擊精準。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=45,
            element="wind",
            effects=("self_buff_apply:afterimage_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_chain_step", 3),),
        ),
        # 風 — 賢者（機動路線・終點）
        _spell(
            "haste_domain",
            "神速領域",
            "展開神速領域，大幅提升領域內全體同伴的速度與迴避。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=70,
            element="wind",
            effects=("buff_apply:haste_domain_haste",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("afterimage_step", 5),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 風 — 學徒（破壞路線・根）
        _spell(
            "wind_blade",
            "風刃術",
            "颳起銳利風刃，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=14,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            effect_policies=(EffectPolicy(coefficient=0.7),),
        ),
        # 風 — 術師（破壞路線・分支點）
        _spell(
            "tornado_blade",
            "龍捲風刃",
            "捲起龍捲風刃，對單一目標造成高額魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=26,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("wind_blade", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 風 — 大師（破壞路線・暴風分支）
        _spell(
            "storm_domain",
            "暴風領域",
            "展開暴風領域，對範圍內所有敵人造成魔法傷害並擊退敵人。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("tornado_blade", 3),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.4),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 風 — 大師（破壞路線・刃舞分支）
        _spell(
            "gale_dance_strike",
            "疾風刃舞",
            "以疾風之勢舞動刃擊，對單一目標造成連續兩次魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=40,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("tornado_blade", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(extra_strikes=1),
                ),
            ),
        ),
        # 風 — 賢者（破壞路線・暴風分支）
        _spell(
            "heavens_wrath_storm",
            "天譴風暴",
            "喚起天譴風暴，對範圍內所有目標造成極高魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("storm_domain", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 風 — 賢者（破壞路線・刃舞分支）
        _spell(
            "sky_rending_slash",
            "天穹裂斬",
            "聚風成刃撕裂天穹，對單一目標造成極高魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_dance_strike", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 風 — 主宰（破壞路線・暴風分支終點）
        _spell(
            "sky_tempest",
            "蒼穹暴風",
            "召喚蒼穹暴風，對範圍內所有敵人造成毀滅級魔法傷害並附加擊退控制。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced_tempest"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("heavens_wrath_storm", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 風 — 主宰（破壞路線・刃舞分支終點・處決級）
        _spell(
            "vacuum_severance",
            "真空斬滅",
            "斬出真空之刃，對單一目標造成處決級魔法傷害（無視防禦）。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("sky_rending_slash", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 風 — 神格（兩線匯合・樹冠）
        _spell(
            "sky_apotheosis",
            "天穹神格",
            "展現天穹神格，對範圍內所有敵人造成毀滅級魔法傷害並附加擊退控制 90 秒。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=220,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced_apotheosis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(
                SkillPrerequisite("sky_tempest", 10),
                SkillPrerequisite("vacuum_severance", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
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
            category=SkillCategory.ENHANCEMENT,
            group="身法",
        ),
        # 雷 — 學徒（先制路線・根）
        _spell(
            "static_ward",
            "靜電護罩",
            "以靜電護罩，隨時反擊近身之敵。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=10,
            element="lightning",
            effects=("self_buff_apply:lightning_static_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            effect_policies=(EffectPolicy(),),
        ),
        # 雷 — 術師（先制路線）
        _spell(
            "lightning_flicker",
            "雷光連閃",
            "雷光連閃，使自身行動順序提前並提升麻痺微階觸發率。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=22,
            element="lightning",
            effects=(
                "self_buff_apply:lightning_flicker_ward",
                "self_buff_apply:flicker_advance",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("static_ward", 3),),
            effect_policies=(EffectPolicy(), EffectPolicy()),
        ),
        # 雷 — 大師（先制路線・分支點）
        _spell(
            "thunder_combo",
            "雷霆連擊",
            "以雷霆之勢連續攻擊，對單一目標造成多段魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=46,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("lightning_flicker", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(extra_strikes=2),
                ),
            ),
        ),
        # 雷 — 賢者（先制路線）
        _spell(
            "thunder_gods_haste",
            "雷神之速",
            "獲得雷神之速，追加行動機會。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=68,
            element="lightning",
            effects=("self_buff_apply:lightning_extra_action",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_combo", 5),),
            effect_policies=(EffectPolicy(),),
        ),
        # 雷 — 賢者（先制路線・分支終點）
        _spell(
            "thunder_shatter_strike",
            "碎雷連擊",
            "將雷霆連擊技巧磨練至極致，對單一目標造成高額魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_combo", 5),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 雷 — 主宰（先制路線・處決級）
        _spell(
            "judgement_thunder",
            "審判雷霆",
            "喚起審判雷霆，無視防禦對單一目標造成處決級魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_gods_haste", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 雷 — 學徒（過載路線・根）
        _spell(
            "spark_shock",
            "電擊術",
            "凝聚雷之魔力電擊，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=13,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 雷 — 術師（過載路線・分支點）
        _spell(
            "chain_lightning",
            "雷鎖術",
            "釋放連鎖閃電，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=27,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("spark_shock", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 雷 — 術師（過載路線・分支點）
        _spell(
            "paralyzing_bolt",
            "麻痺電擊",
            "射出麻痺電擊，對單一目標造成魔法傷害並使其麻痺。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="lightning",
            effects=("damage:lightning:magic", "buff_apply:paralysis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("spark_shock", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
            ),
        ),
        # 雷 — 大師（過載路線）
        _spell(
            "lightning_strike",
            "落雷術",
            "召喚落雷，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("chain_lightning", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 雷 — 大師（過載路線・分支終點）
        _spell(
            "thunder_prison",
            "雷獄囚縛",
            "引雷凝聚成獄囚縛目標，造成魔法傷害並附加強化版麻痺。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="lightning",
            effects=("damage:lightning:magic", "buff_apply:paralysis_enhanced"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("paralyzing_bolt", 3),),
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(),
            ),
        ),
        # 雷 — 賢者（過載路線）
        _spell(
            "heavens_thunder",
            "天雷降臨",
            "召喚天雷降臨，對範圍內所有目標造成極高魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=92,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("lightning_strike", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 雷 — 主宰（過載路線・毀滅級）
        _spell(
            "divine_lightning_slaughter",
            "神雷滅殺",
            "召喚神雷滅殺一切，對範圍內所有敵人造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=155,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("heavens_thunder", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 雷 — 神格（兩線匯合・樹冠）
        _spell(
            "thunder_apotheosis",
            "雷霆神格",
            "化身雷霆神格，對範圍內所有敵人造成毀滅級魔法傷害，並將受擊目標當輪行動順序推至最後。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="lightning",
            effects=(
                "damage:lightning:magic",
                "buff_apply:apotheosis_retreat",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(
                SkillPrerequisite("judgement_thunder", 10),
                SkillPrerequisite("divine_lightning_slaughter", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 冰 — 學徒（遲緩路線・根）
        _spell(
            "frost_breath",
            "凍結之息",
            "吐出極寒凍氣，使目標陷入遲緩。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="ice",
            effects=("buff_apply:ice_slow",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
        ),
        # 冰 — 術師（遲緩路線・分支點）
        _spell(
            "ice_wall",
            "冰牆術",
            "築起冰霜之牆，於目標周邊結霜成牆並對進出者附加遲緩。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=25,
            element="ice",
            effects=("buff_apply:ice_wall_frost", "buff_apply:ice_slow"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("frost_breath", 3),),
        ),
        # 冰 — 大師（遲緩路線・泥沼分支終點）
        _spell(
            "frost_mire",
            "凝霜泥沼",
            "使範圍地面霜化成泥沼，使停留在其上的敵人大幅降低敏捷。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="ice",
            effects=("buff_apply:ice_frost_mire",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_wall", 3),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
        ),
        # 冰 — 大師（遲緩路線・永凍分支）
        _spell(
            "permafrost_domain",
            "永凍領域",
            "展開永凍領域，使範圍內所有目標陷入凍結無法行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="ice",
            effects=("buff_apply:ice_freeze",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_wall", 3),),
        ),
        # 冰 — 賢者（遲緩路線・永凍分支）
        _spell(
            "absolute_tundra",
            "絕對凍土",
            "將大地化為絕對凍土，對範圍內所有敵人造成魔法傷害並使其凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=82,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_tundra"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("permafrost_domain", 8),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 冰 — 主宰（遲緩路線・永凍分支終點・毀滅級）
        _spell(
            "eternal_ice_field",
            "長夜冰原",
            "展開無盡長夜的極寒冰原，對範圍內所有敵人造成毀滅級魔法傷害並附加凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=158,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_nightfall"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("absolute_tundra", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 冰 — 學徒（監禁路線・根）
        _spell(
            "ice_shard",
            "冰錐術",
            "凝聚冰之魔力化為銳利冰錐，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=13,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 冰 — 術師（監禁路線）
        _spell(
            "frost_arrow_rain",
            "冷凍箭雨",
            "降下銳利冷凍箭雨，對範圍內所有敵人造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=28,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_shard", 3),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.0),
            ),
        ),
        # 冰 — 大師（監禁路線・分支點）
        _spell(
            "ice_prison",
            "冰封監牢",
            "以寒冰凝成監牢，對單一目標施加定身封鎖其行動。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="ice",
            effects=("buff_apply:ice_prison",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("frost_arrow_rain", 3),),
        ),
        # 冰 — 賢者（監禁路線・暴風分支）
        _spell(
            "blizzard",
            "暴風雪",
            "喚起狂暴暴風雪，對範圍內所有敵人造成高額魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=88,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_prison", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
            ),
        ),
        # 冰 — 賢者（監禁路線・碎裂分支終點）
        _spell(
            "crystal_shatter",
            "冰晶爆裂",
            "引爆目標身上的冰霜碎屑，對凍結或定身狀態的目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_prison", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(
                        predicate=(
                            "buff:ice_freeze",
                            "buff:ice_freeze_tundra",
                            "buff:ice_freeze_nightfall",
                            "buff:ice_freeze_apotheosis",
                            "buff:ice_prison",
                        ),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 冰 — 主宰（監禁路線・暴風分支終點・處決級）
        _spell(
            "absolute_zero",
            "絕對零度",
            "釋放極致寒氣，對單一目標造成無視防禦的處決級魔法傷害並附加凍結。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=140,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_nightfall"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("blizzard", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
                EffectPolicy(),
            ),
        ),
        # 冰 — 神格（兩線匯合・樹冠・毀滅級）
        _spell(
            "eternal_frost_apotheosis",
            "永凍神格",
            "顯現永凍神格，對範圍內所有敵人造成毀滅級魔法傷害並附加超長凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_apotheosis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(
                SkillPrerequisite("eternal_ice_field", 10),
                SkillPrerequisite("absolute_zero", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 光 — 學徒
        _spell(
            "heal",
            "治癒術",
            "以光之魔力治癒，恢復單一目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        _spell(
            "light_arrow",
            "光箭術",
            "射出光之箭矢，對單一目標造成魔法傷害，對暗屬性或不死系目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=14,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            effect_policies=(
                EffectPolicy(
                    coefficient=1.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 光 — 術師
        _spell(
            "mass_heal",
            "群體治癒",
            "施展群體治癒，恢復範圍內所有目標的生命力。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=30,
            element="light",
            effects=("heal:area",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("heal", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        _spell(
            "purify",
            "淨化術",
            "以淨化之光，解除單一目標的異常狀態。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=22,
            element="light",
            effects=("cleanse:status",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("light_arrow", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        _spell(
            "penitent_touch",
            "懺悔之觸",
            "以懺悔之觸碰造成光魔法傷害，對近期有強迫行為之目標追加一次審判打擊。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=27,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("purify", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=1.4,
                    damage=DamagePolicy(
                        predicate=("undead",),
                        attack_multiplier=1.5,
                        repeat_when="forced_interaction",
                        extra_strikes=1,
                    ),
                ),
            ),
        ),
        # 光 — 大師
        _spell(
            "advanced_heal",
            "高級治癒",
            "施展高級治癒，大量恢復單一目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=46,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("mass_heal", 3),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        _spell(
            "sanctified_ward",
            "聖光庇護陣",
            "佈下聖光庇護陣，賦予範圍內所有目標持續回復生命力的庇護。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="light",
            effects=("buff_apply:sanctified_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("advanced_heal", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        _spell(
            "judgment_strike",
            "聖裁斬",
            "凝聚聖裁之力斬向目標，對暗屬性或不死系目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("penitent_touch", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 光 — 賢者
        _spell(
            "revival_light",
            "復甦之光",
            "綻放復甦之光，大量恢復瀕危目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=82,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("advanced_heal", 5),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        _spell(
            "holy_radiance",
            "神聖光輝",
            "綻放神聖光輝，對敵方造成光魔法傷害，同時淨化自身與友方的異常狀態。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="light",
            effects=("damage:light:magic", "cleanse:status"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("judgment_strike", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
        # 光 — 主宰
        _spell(
            "goddess_blessing",
            "女神降福",
            "獲得女神的祝福，大量恢復範圍內所有目標的生命力並強化防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="light",
            effects=("heal:area", "buff_apply:light_blessing"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("revival_light", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8), EffectPolicy()),
        ),
        _spell(
            "holy_kiss_heal",
            "聖吻之癒〔聖禮〕",
            "施展聖吻聖儀，雙方皆需處於微興奮以上，以興奮序數提升治癒威力並施加常規刺激。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="light",
            effects=("heal:single", "stimulus:both"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("revival_light", 8),),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"field": "arousal", "gte": "微興奮"}),
                CastCondition(CastConditionSubject.EACH_TARGET, {"field": "arousal", "gte": "微興奮"}),
            ),
            interaction=InteractionPolicy(
                contact=True,
                distinct_participants=True,
                target_capable=False,
                resistible=True,
            ),
            effect_policies=(
                EffectPolicy(
                    magnitude=StateMagnitude(
                        subject=StateMagnitudeSubject.ACTOR,
                        field="arousal",
                        base=3.2,
                        per_ordinal=0.2,
                        maximum=4.0,
                        marker="climax_empowerment",
                    )
                ),
                EffectPolicy(),
            ),
        ),
        _spell(
            "goddess_milk",
            "女神之乳〔聖禮〕",
            "施展授乳聖儀，透過接觸儀式大量治療並淨化異常狀態，對目標施加依施法者有效露出加成的刺激。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=140,
            element="light",
            effects=("heal:single", "cleanse:status", "stimulus:target"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("holy_kiss_heal", 3),),
            interaction=InteractionPolicy(
                contact=True,
                distinct_participants=True,
                target_capable=True,
                resistible=True,
            ),
            effect_policies=(
                EffectPolicy(coefficient=2.8),
                EffectPolicy(),
                EffectPolicy(
                    stimulus_bonus=StateMagnitude(
                        subject=StateMagnitudeSubject.ACTOR,
                        field="effective_exposure",
                        base=0.0,
                        per_ordinal=2.0,
                        maximum=8.0,
                        marker="climax_empowerment",
                    )
                ),
            ),
        ),
        _spell(
            "blessed_climax",
            "天賜高潮〔聖禮〕",
            "施法者強行推進快感至極限並進入高潮期相，以超位階威力治療我方全體。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=170,
            element="light",
            effects=("heal:area", "pleasure_peak"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("goddess_milk", 5),),
            effect_policies=(
                EffectPolicy(coefficient=3.4),
                EffectPolicy(audience=EffectAudience.SELF),
            ),
        ),
        _spell(
            "heavens_judgment_light",
            "天啟聖裁",
            "喚起天啟聖裁，對單一目標造成毀滅級魔法傷害，對暗屬性或不死系無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("holy_radiance", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.0,
                        bypass_defense=True,
                    ),
                ),
            ),
        ),
        # 光 — 神格
        _spell(
            "bliss_apotheosis",
            "至福神格",
            "神格之光降臨，治癒我方全體並重創敵方，附加目標最大生命值比例傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=240,
            element="light",
            effects=("heal:area", "damage:light:magic"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(
                SkillPrerequisite("blessed_climax", 10),
                SkillPrerequisite("heavens_judgment_light", 10),
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ALLIES, coefficient=3.8),
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.6,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 暗 — 學徒（詛咒路線・根）
        _spell(
            "weaken",
            "衰弱術",
            "施展衰弱術，降低單一目標的攻擊力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="dark",
            effects=("buff_apply:dark_weaken",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 術師（詛咒路線・分支點）
        _spell(
            "curse",
            "詛咒術",
            "施展詛咒術，削弱單一目標的攻擊、防禦與敏捷。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=26,
            element="dark",
            effects=("buff_apply:dark_curse",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("weaken", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 大師（詛咒路線・純減益分支）
        _spell(
            "curse_spread",
            "詛咒擴散",
            "擴散詛咒之力，削弱範圍內全體目標的攻擊與防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="dark",
            effects=("buff_apply:dark_spread",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 賢者（詛咒路線・控場分支終點）
        _spell(
            "dark_dominion",
            "黑暗支配",
            "展開黑暗支配，使範圍內所有目標陷入恐懼無法行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=72,
            element="dark",
            effects=("buff_apply:fear",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse_spread", 5),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 大師（詛咒路線・侵蝕分支）
        _spell(
            "shadow_torture",
            "暗影之刑",
            "對單一目標施以暗影之刑，造成高額魔法傷害並附著侵蝕，流失全額轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=41,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse", 3),),
            effect_policies=(EffectPolicy(coefficient=2.0), EffectPolicy()),
        ),
        # 暗 — 賢者（詛咒路線・深層侵蝕）
        _spell(
            "shadow_blight",
            "暗影侵蝕",
            "注入深層暗影侵蝕，造成巨量魔法傷害並附著深層侵蝕，流失全額轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion_deep"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_torture", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8), EffectPolicy()),
        ),
        # 暗 — 主宰（詛咒路線・處決匯合支）
        _spell(
            "underworld_judgment",
            "冥界審判",
            "喚起冥界審判，對單一目標造成處決級魔法傷害，無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_blight", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 暗 — 學徒（吞噬路線・根）
        _spell(
            "shadow_bolt",
            "暗影箭",
            "射出暗影之箭，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=14,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 暗 — 術師（吞噬路線）
        _spell(
            "dark_burst",
            "闇裂術",
            "釋放闇之爆裂，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=29,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_bolt", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 暗 — 大師（吞噬路線）
        _spell(
            "dark_corrosion_domain",
            "闇蝕領域",
            "展開闇蝕領域，對範圍內所有目標造成魔法傷害並附著侵蝕，受蝕者流失全額轉入施法者。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=47,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("dark_burst", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4), EffectPolicy()),
        ),
        # 暗 — 賢者（吞噬路線・處決）
        _spell(
            "abyss_devour",
            "深淵吞噬",
            "召喚深淵吞噬目標，對單一目標造成處決級魔法傷害，無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=85,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("dark_corrosion_domain", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 暗 — 主宰（吞噬路線・毀滅＋自癒）
        _spell(
            "void_annihilation",
            "虛空湮滅",
            "召喚湮滅萬物的虛空，對範圍內所有目標造成毀滅級魔法傷害，並命中回復施法者已損 HP 的 10%。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=155,
            element="dark",
            effects=("damage:dark:magic", "self_heal:missing_fraction:0.1"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("abyss_devour", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(),
            ),
        ),
        # 暗 — 神格（兩根匯合頂點・樹冠）
        _spell(
            "abyssal_apotheosis",
            "深淵神格",
            "展現深淵終極神格，對範圍內所有目標造成毀滅級魔法傷害，施加巨幅削弱，並命中回復施法者已損 HP 的 15%。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="dark",
            effects=(
                "damage:dark:magic",
                "buff_apply:dark_apotheosis",
                "self_heal:missing_fraction:0.15",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(
                SkillPrerequisite("underworld_judgment", 10),
                SkillPrerequisite("void_annihilation", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        _skill(
            "dual_wield_style",
            "雙持劍術",
            "同時揮舞兩把武器進行戰鬥的架式。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["weapon_style:dual_wield"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        _skill(
            "dual_blade_mastery",
            "雙刃旋舞",
            "以旋舞般的雙刀連擊，對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
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
            category=SkillCategory.ENHANCEMENT,
            group="身法",
        ),
        _skill(
            "concentration",
            "集中",
            "凝聚精神，暫時提升自身的專注與準確度。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            cost={"mp": 5},
            effects=["self_buff_apply:focus"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "defense_instinct",
            "防禦直覺",
            "被動強化自身的防禦能力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:defense_small"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "pain_to_pleasure",
            "痛苦轉換",
            "每次實際受傷或首次取得負面狀態時，將痛苦轉化為快感。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "priestly_grace",
            "女神近接",
            "以自身興奮強化聖光庇護的回復效果。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "blade_art_mastery",
            "劍術精通",
            "被動提昇劍術與刀術相關技能的效果。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:blade_arts"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "extreme_endurance",
            "極限耐力",
            "被動強化自身的耐力上限。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:endurance_extreme"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "magic_circle_comprehension",
            "魔法陣理解",
            "被動提昇對魔法陣的理解與運用。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:magic_circle_comprehension"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "precise_mana_control",
            "精準魔力控制",
            "被動強化對魔力的精準控制。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:mana_precision"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "retainer_martial_training",
            "隨從武藝訓練",
            "被動提昇隨從角色的武藝水準。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:retainer_training"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "guardian_instinct",
            "護主本能",
            "被動強化守護主人、忠誠護衛的本能。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_buff:guardian_instinct"],
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "elf_longevity",
            "精靈長壽",
            "被動延長生命週期，是精靈種族的特質。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["passive_trait:elf_longevity"],
            category=SkillCategory.ENHANCEMENT,
            group="天賦",
        ),
        _skill(
            "reincarnation_boon_elosia",
            "轉生祝福·伊洛希雅",
            "轉生帶來的祝福，被動加速魔力成長。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["growth_rate:practice:100"],
            category=SkillCategory.ENHANCEMENT,
            group="天賦",
        ),
        _skill(
            "reincarnation_boon_yuka",
            "轉生祝福·悠花",
            "轉生帶來的祝福，被動強化戰鬥預感。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            effects=["combat_prediction:武感"],
            category=SkillCategory.ENHANCEMENT,
            group="天賦",
        ),
        _skill(
            "reincarnation_boon_yuna",
            "轉生祝福·悠奈",
            "轉生帶來的祝福，被動精通性魔法的掌握。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
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
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["sexual_magic_mastery"],
            category=SkillCategory.SEXUAL_ACT,
            group="精通",
        ),
        # ------------------------------------------------------------------
        # 神之秘法 (DIVINE_MYSTERY): the three known chains plus the
        # three-parent convergence node, transcribed from the authored node
        # table (docs/lore/skill-trees/divine-mystery.md section 2).
        #
        # Every node is zero-cost, bloodline-gated and usable outside
        # combat. Grant scales and the party audience live in the
        # per-occurrence EffectPolicy (conferral-grant-store D4/D3), so the
        # category declares no damage or healing effect and derives no MP
        # cost band (spell_tier_for stays None for every member). Chain
        # depth is expressed by prerequisite edges and the derived tip cap.
        # ------------------------------------------------------------------
        # 統御線 — "power belongs to the one who earned it".
        _skill(
            "dominion_art",
            "統御術",
            "授予目標一部分自身技能的效果。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            # The lore prices this root at 一成 (0.10): the scale is the
            # per-occurrence coefficient the conferral handlers read, so the
            # shipped verb records grants at the priced strength from the
            # moment the mechanism becomes castable.
            effect_policies=(EffectPolicy(coefficient=0.1),),
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "dominion_recall",
            "權能收回",
            "解除目標身上的一切技能授予與成長授予，不論來源為何。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["revoke_grants"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("dominion_art", 3),),
        ),
        _skill(
            "shared_dominion",
            "共權統御",
            "把施法者持有的同一批可授予被動，一次覆蓋全隊。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            effect_policies=(
                EffectPolicy(coefficient=0.1, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("dominion_art", 3),),
        ),
        _skill(
            "sovereign_investiture",
            "王權授予",
            "以更高的授予強度，把施法者持有的可授予被動覆蓋全隊。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            effect_policies=(
                EffectPolicy(coefficient=0.25, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("shared_dominion", 3),),
        ),
        # 傳承線 — "learning takes time".
        _skill(
            "mentors_covenant",
            "師徒契約",
            "把自身的學習節奏借給目標，加速其熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(EffectPolicy(coefficient=1.5),),
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "chorus_of_ages",
            "世代合誦",
            "把自身的學習節奏借給全隊，加速熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(
                EffectPolicy(coefficient=1.5, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("mentors_covenant", 3),),
        ),
        _skill(
            "undying_tutelage",
            "不朽教誨",
            "以近乎精靈的學習節奏覆蓋全隊，大幅加速熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(
                EffectPolicy(coefficient=3.0, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("chorus_of_ages", 3),),
        ),
        # 帷幕線 — "what you see is what is real".
        _skill(
            "status_disguise",
            "狀態偽裝",
            "以神之秘法偽裝自身的外貌與部分能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["set_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "bestowed_veil",
            "賜帷",
            "把帷幕蓋到目標身上，改寫其顯示層的外貌與能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["set_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("status_disguise", 3),),
        ),
        _skill(
            "unveiling_eye",
            "揭帷之眼",
            "清除目標身上非神性來源的偽裝層。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["reveal_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("status_disguise", 3),),
        ),
        _skill(
            "true_name_sight",
            "真名之視",
            "清除目標身上任何來源的偽裝層，包含神之秘法級的帷幕。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["reveal_disguise:true_name"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("unveiling_eye", 5),),
        ),
        # 匯合 — the capstone waits for all three chain ends at Lv.10.
        _skill(
            "crown_apotheosis",
            "冠冕神格",
            "把三條秘法之鏈的極限同時授予全隊：授予力量、借出成長、蓋上帷幕。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=[
                "confer_skill_partial",
                "confer_growth_rate",
                "set_disguise",
            ],
            effect_policies=(
                EffectPolicy(coefficient=0.5, audience=EffectAudience.ALLIES),
                EffectPolicy(coefficient=5.0, audience=EffectAudience.ALLIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(
                SkillPrerequisite("sovereign_investiture", 10),
                SkillPrerequisite("undying_tutelage", 10),
                SkillPrerequisite("true_name_sight", 10),
            ),
        ),
    )
}


# ---------------------------------------------------------------------------
# Skill-lineage graph validation (use-driven-progression design §9.3)
# ---------------------------------------------------------------------------

# skill_key -> the edges that CONSUME it, as ``(consumer_key,
# min_proficiency)`` pairs, ascending by threshold. Computed and cached by
# :func:`validate_prerequisite_graph` at registry load; the tip-cap
# derivation reads this cache in O(1) and never walks the registry again.
_LINEAGE_CONSUMERS: dict[str, tuple[tuple[str, int], ...]] = {}

# skill_key -> declared edges, in registry order (same load-time cache).
_LINEAGE_PREREQS: dict[str, tuple[SkillPrerequisite, ...]] = {}


def prerequisite_consumers(skill_key: str) -> tuple[tuple[str, int], ...]:
    """Return the cached consuming edges ``(consumer_key, min_proficiency)``.

    Reads the load-time cache built by ``validate_prerequisite_graph``; an
    unknown key yields ``()`` (a skill nobody consumes is a lineage canopy).
    """
    return _LINEAGE_CONSUMERS.get(skill_key, ())


def declared_prerequisites(skill_key: str) -> tuple[SkillPrerequisite, ...]:
    """Return the cached declared edges of one skill (``()`` when unknown)."""
    return _LINEAGE_PREREQS.get(skill_key, ())


def validate_prerequisite_graph(
    registry: dict[str, SkillDef],
) -> dict[str, tuple[tuple[str, int], ...]]:
    """Fail closed on an invalid lineage graph; cache and return the reverse map.

    Load-time rules (design §9.3), every violator named:

    1. every ``prerequisites.skill_key`` exists in ``registry``;
    2. the graph is acyclic — a Kahn topological sort; leftover nodes are
       reported as a named cycle;
    3. every ``min_proficiency`` is an int >= 1 (the dataclass constructor
       enforces the same rule per entry; this pass names the owning skill);
    4. a skill with no prerequisites is a tree root (no extra flag exists);
    5. the reverse-edge map is computed and cached for O(1) tip-cap lookup.

    The structure is an n-ary DAG: any number of edges may consume one node
    (branching) and one skill may declare any number of prerequisites
    (merging); the rules above are degree-independent. Idempotent, so the
    sexual-act sidecar re-runs it after extending the registry.
    """
    consumers: dict[str, list[tuple[str, int]]] = {}
    prereqs: dict[str, tuple[SkillPrerequisite, ...]] = {}
    for key, skill in registry.items():
        if not skill.prerequisites:
            continue
        prereqs[key] = tuple(skill.prerequisites)
        for prereq in skill.prerequisites:
            if prereq.skill_key not in registry:
                raise ValueError(
                    f"skill {key!r} declares prerequisite {prereq.skill_key!r} "
                    "which is not in SKILL_REGISTRY"
                )
            if prereq.min_proficiency < 1:
                raise ValueError(
                    f"skill {key!r} declares min_proficiency "
                    f"{prereq.min_proficiency} for {prereq.skill_key!r}; the "
                    "threshold must be >= 1"
                )
            consumers.setdefault(prereq.skill_key, []).append(
                (key, prereq.min_proficiency)
            )

    # Kahn topological sort over the prerequisite edges (prereq -> consumer).
    indegree = {key: len(prereqs.get(key, ())) for key in registry}
    queue = sorted(key for key, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.pop(0)
        visited += 1
        for consumer_key, _ in sorted(consumers.get(current, ())):
            indegree[consumer_key] -= 1
            if indegree[consumer_key] == 0:
                queue.append(consumer_key)
                queue.sort()
    if visited != len(registry):
        cycle = sorted(key for key, degree in indegree.items() if degree > 0)
        raise ValueError(
            "skill prerequisite graph is cyclic; the offending nodes are "
            f"{cycle!r} (every listed skill either prereqs a cycle member or "
            "is consumed by one)"
        )

    reverse = {
        key: tuple(sorted(edges, key=lambda edge: (edge[1], edge[0])))
        for key, edges in consumers.items()
    }
    _LINEAGE_CONSUMERS.clear()
    _LINEAGE_CONSUMERS.update(reverse)
    _LINEAGE_PREREQS.clear()
    _LINEAGE_PREREQS.update(prereqs)
    return reverse


validate_prerequisite_graph(SKILL_REGISTRY)
