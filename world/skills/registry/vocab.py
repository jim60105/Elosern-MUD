"""Skill-definition vocabulary: enums, bounds, and the frozen ``SkillDef``.

Part of the :mod:`world.skills.registry` package (design section 5.2 and
``skills-equipment``): the shared field contract every data slice and the
lineage validator import; the seed builders live in
:mod:`world.skills.registry.builders`.

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
    HOLY_RITE = "holy_rite"


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
