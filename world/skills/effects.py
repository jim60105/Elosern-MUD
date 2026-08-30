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
# ``growth_rate:practice:<multiplier>`` convention (the retired
# ``growth_rate:magic:<N>`` prefix fails closed at parse).
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


# Ownership-triggered movement waivers (flight/flash_step are PASSIVE).
@dataclass(frozen=True)
class MovementEffect:
    """Name the movement mode granted by owning this skill.

    The waiver set is consumed by ``world.rules.movement.charge_movement``:
    owning ``flight`` waives the ``wilderness_move`` clock cost, and owning
    either mode passes any exit marked ``requires_flight``.
    """

    mode: Literal["flight", "flash_step"]


@dataclass(frozen=True)
class WeaponStyleEffect:
    """Name the weapon stance this skill enters.

    ``light_sword`` is no longer a ``weapon_style`` value — its skill moved to
    the ``damage`` convention. The remaining stance case (``dual_wield``) is
    consumed by the ``combat_modifiers.yaml`` rule table via the ``skill_owned``
    and ``dual_wielding`` conditions.
    """

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
class ActorSexualEventEffect:
    """Resolve one rule-driven sexual transition on the performing actor only.

    The actor-scoped sibling of ``SexualEventEffect``: an act declaring a
    performer-scoped event (``self_exposure``, ``public_exposure``,
    ``watched_during_activity``, ``public_sexual_activity``) emits it through
    the ``sexual_event_actor:<name>`` string, and the cast-side handler
    applies the named event to the acting entity, never to a target.
    """

    event_name: str


@dataclass(frozen=True)
class PleasureEffect:
    """Apply one sexual act's pleasure to every participant of its cast.

    The parsed segment is the acting ``SexualActDef``'s own key; every other
    parameter (base magnitude, body parts, actor ratio, participant count)
    is read from ``SEXUAL_ACT_REGISTRY[act_key]`` at cast time so no value is
    duplicated between the registry and the effect string.
    """

    act_key: str


@dataclass(frozen=True)
class SexualCounterEffect:
    """Increment the counters one sexual act declares on its participants.

    ``actor_counters`` land on the acting entity and
    ``participant_counters`` on every other participant; the counter names
    themselves are read from ``SEXUAL_ACT_REGISTRY[act_key]`` at cast time.
    """

    act_key: str


@dataclass(frozen=True)
class PairEventEffect:
    """Resolve one sex-conditional rule event from a cast's participant pair.

    The parsed segment is the acting ``SexualActDef``'s own key; the
    per-sex-pair event table is read from ``SEXUAL_ACT_REGISTRY[act_key]`` at
    cast time so no value is duplicated between the registry and the effect
    string. A cast whose participants match no declared pair resolves no
    event and stages no effect (the ``other``/unknown D-12 branch).
    """

    act_key: str


# 神之秘法 act effects (divine-sexual-arts-reuse): hand-built acts declare
# these instead of the ordinary pleasure:/sexual_counter: triad. Each is a
# general dispatch-table entry — no handler reads ``requires_divine_arts``
# or the caller's line.
@dataclass(frozen=True)
class DivinePleasureMaxEffect:
    """Set every resolved target's pleasure to its ceiling in one cast.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the target set comes from the cast's resolved targets,
    and the handler reuses the shipped ``_apply_pleasure_gain`` twice
    (``gain=100`` then ``gain=0``) to walk the climax cycle into 進行中.
    """


@dataclass(frozen=True)
class ClimaxExtensionStageEffect:
    """Stage ``count`` consecutive climax extensions on every resolved target."""

    count: int


@dataclass(frozen=True)
class SexualDrainEffect:
    """Drain one target's pleasure into the caster's MP, SP, and HP.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler reads the target's pleasure itself.
    """


@dataclass(frozen=True)
class SaturateSensitivityEffect:
    """Pin every resolvable body part's sensitivity to the top level.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.saturate_sensitivity()``
    on each resolved non-actor target.
    """


@dataclass(frozen=True)
class ClampShameEffect:
    """Pin the target's shame at the vocabulary ceiling (成癮).

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.clamp_shame_to("成癮")``
    on each resolved non-actor target, eagerly rejecting a ``Monster`` target
    before staging anything.
    """


@dataclass(frozen=True)
class MarkSubmissionEffect:
    """Mark the target as permanently auto-complying toward the caster.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls
    ``target.sexual.mark_submission(str(actor.id))`` on each resolved
    non-actor target, keying the permanent mark by the caster's unique
    database id.
    """


@dataclass(frozen=True)
class RestorePurityEffect:
    """Restore the target's virgin flag without touching experience_types.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.restore_purity()``
    on each resolved non-actor target.
    """


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
class HealEffect:
    """Restore HP to every resolved target, capped at each target's maximum."""

    shape: Literal["single", "area"]


@dataclass(frozen=True)
class SelfHealEffect:
    """Restore the acting entity's HP, capped at the caster's maximum."""


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
        if stat != "practice":
            raise ValueError(
                f"growth_rate effect stat must be 'practice', got {stat!r} "
                f"in {effect_id!r} (the retired 'magic' key fails closed)"
            )
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
        mode = _parse_single_arg(effect_id, prefix)
        if mode not in ("flight", "flash_step"):
            raise ValueError(
                f"movement effect mode must be flight or flash_step, got {effect_id!r}"
            )
        return MovementEffect(mode=mode)
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
    if prefix == "sexual_event_actor":
        return ActorSexualEventEffect(event_name=_parse_single_arg(effect_id, prefix))
    if prefix == "pleasure":
        return PleasureEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "sexual_counter":
        return SexualCounterEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "act_pair_event":
        return PairEventEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "divine_pleasure_max":
        _parse_single_arg(effect_id, prefix)
        return DivinePleasureMaxEffect()
    if prefix == "divine_climax_extension_stage":
        try:
            count = int(_parse_single_arg(effect_id, prefix))
        except ValueError as error:
            raise ValueError(
                f"divine_climax_extension_stage count must be an integer, "
                f"got {effect_id!r}"
            ) from error
        if count < 1:
            raise ValueError(
                f"divine_climax_extension_stage count must be positive, "
                f"got {effect_id!r}"
            )
        return ClimaxExtensionStageEffect(count=count)
    if prefix == "divine_drain":
        _parse_single_arg(effect_id, prefix)
        return SexualDrainEffect()
    if prefix == "divine_saturate_sensitivity":
        _parse_single_arg(effect_id, prefix)
        return SaturateSensitivityEffect()
    if prefix == "divine_clamp_shame":
        _parse_single_arg(effect_id, prefix)
        return ClampShameEffect()
    if prefix == "divine_mark_submission":
        _parse_single_arg(effect_id, prefix)
        return MarkSubmissionEffect()
    if prefix == "divine_restore_purity":
        _parse_single_arg(effect_id, prefix)
        return RestorePurityEffect()
    if prefix == "damage":
        _, _, rest = effect_id.partition(":")
        element, _, school = rest.partition(":")
        if not element or not school or ":" in school:
            raise ValueError(
                f"damage effect must be damage:<element>:<school>, got {effect_id!r}"
            )
        return DamageEffect(element=element, school=school)
    if prefix == "heal":
        shape = _parse_single_arg(effect_id, prefix)
        if shape not in {"single", "area"}:
            raise ValueError(
                f"heal shape must be 'single' or 'area', got {shape!r}"
            )
        return HealEffect(shape=shape)
    if prefix == "self_heal":
        _parse_bare(effect_id, prefix)
        return SelfHealEffect()
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
