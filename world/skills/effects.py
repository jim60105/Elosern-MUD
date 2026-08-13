"""Typed effect-ID parsing for skill definitions.

Every effect prefix `SKILL_REGISTRY` may declare maps to exactly one frozen
dataclass here. `parse_effect` is the single dispatch point: consumers read
`SkillDef.parsed_effects` (typed instances) instead of re-splitting the raw
string, and an unrecognized prefix raises at registry-load time rather than
silently doing nothing at use time.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

# Continuous-valued ownership effects read by deterministic consumers.
# ``StatMultiplyEffect`` is consumed by ``SkillHandler.effective_value``;
# ``GrowthRateEffect`` mirrors ``world/rules/progression.py``'s existing
# ``growth_rate:magic:<multiplier>`` convention.
@dataclass(frozen=True)
class StatMultiplyEffect:
    """Multiply one stored trait by a fixed factor while owned."""

    trait: str
    multiplier: float


@dataclass(frozen=True)
class GrowthRateEffect:
    """Multiply one growth stat by a fixed factor while owned."""

    stat: str
    multiplier: float


# Ownership-triggered cast-gate overrides (design doc D4, D7).
@dataclass(frozen=True)
class ElementMasteryEffect:
    """Unlock casting of the owning skill's element regardless of magic level.

    The parsed segment is the rank title (``element_mastery_rank:主宰``), not
    an element key; the element itself lives in ``SkillDef.element``.
    """

    rank: str


@dataclass(frozen=True)
class SexualMasteryEffect:
    """Unlock casting of the sex-magic skill family regardless of magic level."""


# Ownership-triggered adjustment bundles resolved by the rule-table engine
# (``combat_modifiers.yaml``) via the ``skill_owned`` condition.
@dataclass(frozen=True)
class RuleTableEffect:
    """Name the rule-table key this passive resolves against."""

    rule_key: str


@dataclass(frozen=True)
class FlavorEffect:
    """A deliberately inert descriptive passive; no consumer reads it."""

    name: str


# Cast-triggered movement and weapon-style effects (handlers land in later
# skill-system-redesign proposals).
@dataclass(frozen=True)
class MovementEffect:
    """Name the movement mode granted by this cast."""

    mode: str


@dataclass(frozen=True)
class WeaponStyleEffect:
    """Name the weapon style this skill enters."""

    style: str


@dataclass(frozen=True)
class DivineMysteryEffect:
    """One divine-mystery entry; ``mechanized`` flags a real cast path."""

    name: str
    mechanized: bool = False


# Thin wrappers for the prefixes with already-working cast handlers in
# ``world/rules/action.py`` and siblings. Their handlers still receive the raw
# string today; the typed instances exist so every declared prefix has one
# faithful representation and later proposals can source handlers from them.
@dataclass(frozen=True)
class ConferralEffect:
    """Grant the target a fractional share of one owned skill's effect."""


@dataclass(frozen=True)
class DisguiseEffect:
    """Replace the target's displayed stats with a disguise override."""


@dataclass(frozen=True)
class BuffApplyEffect:
    """Apply one definition-keyed buff to every target."""

    buff_key: str


@dataclass(frozen=True)
class SelfBuffApplyEffect:
    """Apply one definition-keyed buff to the caster."""

    buff_key: str


@dataclass(frozen=True)
class ConferGrowthRateEffect:
    """Confer the caster's magic-growth rate on one target."""


@dataclass(frozen=True)
class SexualEventEffect:
    """Resolve one rule-driven sexual transition by name."""

    event_name: str


@dataclass(frozen=True)
class DamageEffect:
    """Deal damage of one element and school (``physical``/``magic``)."""

    element: str
    school: str


@dataclass(frozen=True)
class CleanseEffect:
    """Remove every active debuff-polarity buff from each target.

    The parsed segment is the scope (``cleanse:status`` removes all debuff-
    classified active buffs); selective per-buff cleansing is unbuilt.
    """

    scope: Literal["status"]


@dataclass(frozen=True)
class DisengageEffect:
    """Attempt a disengage; the mode names the flavor (e.g. ``self``)."""

    mode: str


def _parse_stat_like(effect_id: str, prefix: str) -> tuple[str, float]:
    """Parse a ``prefix:<stat>:<multiplier>`` effect into its pair."""
    _, _, rest = effect_id.partition(":")
    stat, _, multiplier_text = rest.partition(":")
    if not stat or not multiplier_text:
        raise ValueError(
            f"{prefix} effect must be {prefix}:<stat>:<multiplier>, got {effect_id!r}"
        )
    try:
        multiplier = float(multiplier_text)
    except ValueError as error:
        raise ValueError(
            f"{prefix} multiplier must be numeric, got {effect_id!r}"
        ) from error
    if not isfinite(multiplier):
        raise ValueError(
            f"{prefix} multiplier must be finite, got {effect_id!r}"
        )
    return stat, multiplier


def _parse_single_arg(effect_id: str, prefix: str) -> str:
    """Parse a ``prefix:<arg>`` effect into its bare argument."""
    arg = effect_id.partition(":")[2]
    if not arg:
        raise ValueError(f"{prefix} effect requires an argument, got {effect_id!r}")
    if ":" in arg:
        raise ValueError(
            f"{prefix} effect takes exactly one argument, got {effect_id!r}"
        )
    return arg


def _parse_bare(effect_id: str, prefix: str) -> None:
    """Reject any payload on a prefix that declares none."""
    if effect_id != prefix:
        raise ValueError(
            f"{prefix} effect takes no argument, got {effect_id!r}"
        )


def parse_effect(effect_id: str) -> object:
    """Parse one effect-ID string into its typed frozen dataclass.

    Raises ``ValueError`` for any unrecognized prefix or malformed payload, so
    ``SkillDef.__post_init__`` fails at registry construction instead of the
    effect silently doing nothing at use time.
    """
    prefix = effect_id.partition(":")[0]
    if prefix == "stat_multiply":
        trait, multiplier = _parse_stat_like(effect_id, prefix)
        return StatMultiplyEffect(trait=trait, multiplier=multiplier)
    if prefix == "growth_rate":
        stat, multiplier = _parse_stat_like(effect_id, prefix)
        return GrowthRateEffect(stat=stat, multiplier=multiplier)
    if prefix == "element_mastery_rank":
        return ElementMasteryEffect(rank=_parse_single_arg(effect_id, prefix))
    if prefix == "sexual_magic_mastery":
        _parse_bare(effect_id, prefix)
        return SexualMasteryEffect()
    if prefix == "passive_buff":
        return RuleTableEffect(rule_key=_parse_single_arg(effect_id, prefix))
    if prefix == "combat_prediction":
        return RuleTableEffect(rule_key=_parse_single_arg(effect_id, prefix))
    if prefix == "passive_trait":
        return FlavorEffect(name=_parse_single_arg(effect_id, prefix))
    if prefix == "movement":
        return MovementEffect(mode=_parse_single_arg(effect_id, prefix))
    if prefix == "weapon_style":
        return WeaponStyleEffect(style=_parse_single_arg(effect_id, prefix))
    if prefix == "divine_mystery":
        return DivineMysteryEffect(name=_parse_single_arg(effect_id, prefix))
    if prefix == "confer_skill_partial":
        _parse_bare(effect_id, prefix)
        return ConferralEffect()
    if prefix == "set_disguise":
        _parse_bare(effect_id, prefix)
        return DisguiseEffect()
    if prefix == "buff_apply":
        return BuffApplyEffect(buff_key=_parse_single_arg(effect_id, prefix))
    if prefix == "self_buff_apply":
        return SelfBuffApplyEffect(buff_key=_parse_single_arg(effect_id, prefix))
    if prefix == "confer_growth_rate":
        _parse_bare(effect_id, prefix)
        return ConferGrowthRateEffect()
    if prefix == "sexual_event":
        return SexualEventEffect(event_name=_parse_single_arg(effect_id, prefix))
    if prefix == "damage":
        _, _, rest = effect_id.partition(":")
        element, _, school = rest.partition(":")
        if not element or not school or ":" in school:
            raise ValueError(
                f"damage effect must be damage:<element>:<school>, got {effect_id!r}"
            )
        return DamageEffect(element=element, school=school)
    if prefix == "disengage":
        return DisengageEffect(mode=_parse_single_arg(effect_id, prefix))
    if prefix == "cleanse":
        scope = _parse_single_arg(effect_id, prefix)
        if scope != "status":
            raise ValueError(
                f"cleanse effect must be cleanse:status, got {effect_id!r}"
            )
        return CleanseEffect(scope=scope)
    raise ValueError(f"unrecognized skill effect prefix {prefix!r} in {effect_id!r}")
