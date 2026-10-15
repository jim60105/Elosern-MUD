"""Static target-side polarity of every typed skill effect kind.

The combat panel tells the client whether a skill is hostile and/or
beneficial *to its chosen targets* so a cast aimed across sides can be
confirmed from declared facts alone. The classification is per effect kind
(the dataclass the parser produces), never per amount, formula, or current
participant:

- ``hostile``: the effect harms, drains, debilitates, or sexually acts on the
  recipient.
- ``beneficial``: the effect heals, restores, protects, or grants to the
  recipient.
- ``neutral``: the effect lands only on the actor, is an ownership passive
  read by another consumer, or is inert toward the recipient.
- ``buff-definition``: a buff application takes its buff definition's declared
  ``polarity`` (``debuff`` hostile, ``buff`` beneficial).
- ``gauge-direction``: a gauge transfer takes its declared ``direction``
  (``drain`` hostile, ``restore`` beneficial).

Only effects routed to the chosen targets count: the policy audience is
``SELECTED`` and the parsed recipient is not the actor. For a ``SELF`` skill the
chosen target is the actor, so its ``SELECTED`` effects still count.

``world.skills`` never imports ``world.rules`` (single-writer boundary), so
buff polarity is read from the loaded ``world.rules.buffs`` module when it is
present, or else from the rulebook YAML, mirroring ``_known_buff_keys``.
"""

from collections.abc import Callable
from pathlib import Path
import sys
from typing import Any

from world.skills.effects.combat import (
    CleanseEffect,
    DamageEffect,
    DisengageEffect,
    GaugeTransferEffect,
    HealEffect,
    SelfHealEffect,
)
from world.skills.effects.passives import (
    BuffApplyEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    EffectAudience,
    FlavorEffect,
    GrowthRateEffect,
    MovementEffect,
    RevealDisguiseEffect,
    RevokeGrantsEffect,
    RiteBlessingEffect,
    RiteShelterEffect,
    RuleTableEffect,
    SelfBuffApplyEffect,
    SessionStampEffect,
    SexualMasteryEffect,
    StatMultiplyEffect,
    WeaponStyleEffect,
)
from world.skills.effects.sexual import (
    ActorSexualEventEffect,
    ClampShameEffect,
    ClimaxExtensionStageEffect,
    DivinePleasureMaxEffect,
    MarkSubmissionEffect,
    PairEventEffect,
    PleasureEffect,
    PleasurePeakEffect,
    RestorePurityEffect,
    SaturateSensitivityEffect,
    SexualCounterEffect,
    SexualDrainEffect,
    SexualEventEffect,
    StimulusEffect,
    TargetSexualEventEffect,
)

HOSTILE = "hostile"
BENEFICIAL = "beneficial"
NEUTRAL = "neutral"
BUFF_DEFINITION = "buff-definition"
GAUGE_DIRECTION = "gauge-direction"

POLARITY_CLASSES = frozenset({HOSTILE, BENEFICIAL, NEUTRAL, BUFF_DEFINITION, GAUGE_DIRECTION})

EFFECT_TARGET_POLARITY: dict[type, str] = {
    # combat family
    DamageEffect: HOSTILE,  # deals damage to every resolved target
    CleanseEffect: BENEFICIAL,  # removes the target's debuff-polarity buffs
    HealEffect: BENEFICIAL,  # restores HP to every resolved target
    SelfHealEffect: NEUTRAL,  # restores the actor's own HP, never a target's
    DisengageEffect: NEUTRAL,  # the actor's own disengage attempt
    GaugeTransferEffect: GAUGE_DIRECTION,  # drain takes from, restore gives to the target
    # ownership / passive family
    StatMultiplyEffect: NEUTRAL,  # ownership passive read by the trait handler
    GrowthRateEffect: NEUTRAL,  # ownership passive read by practice growth
    SexualMasteryEffect: NEUTRAL,  # ownership unlock, no recipient
    RuleTableEffect: NEUTRAL,  # ownership rule-table bundle, no recipient
    FlavorEffect: NEUTRAL,  # deliberately inert
    MovementEffect: NEUTRAL,  # ownership movement waiver
    WeaponStyleEffect: NEUTRAL,  # the actor's own stance
    DivineMysteryEffect: NEUTRAL,  # descriptive entry; its mechanics ride other effects
    ConferralEffect: BENEFICIAL,  # grants the target a share of an owned skill
    DisguiseEffect: NEUTRAL,  # cosmetic displayed-stat override, no combat effect
    RevealDisguiseEffect: NEUTRAL,  # lifts a veil; informational, no harm or aid
    BuffApplyEffect: BUFF_DEFINITION,  # takes the applied buff's declared polarity
    SelfBuffApplyEffect: NEUTRAL,  # buffs the actor, never a target
    SessionStampEffect: NEUTRAL,  # stamps the session record
    RiteBlessingEffect: BENEFICIAL,  # mounts a martial blessing buff on the recipient
    RiteShelterEffect: BENEFICIAL,  # grants the recipient a sanctuary rest bonus
    ConferGrowthRateEffect: BENEFICIAL,  # confers the caster's growth rate on the target
    RevokeGrantsEffect: HOSTILE,  # strips every conferral from the target
    # sexual family
    SexualEventEffect: HOSTILE,  # a rule-driven sexual transition on the cast's participants
    ActorSexualEventEffect: NEUTRAL,  # applies to the acting entity only
    TargetSexualEventEffect: HOSTILE,  # a sexual transition on every resolved target
    PleasureEffect: HOSTILE,  # sexual pleasure applied to the participants
    SexualCounterEffect: HOSTILE,  # sexual act counters on the participants
    PairEventEffect: HOSTILE,  # a sex-conditional event from the participant pair
    DivinePleasureMaxEffect: HOSTILE,  # forces each target's pleasure to its ceiling
    ClimaxExtensionStageEffect: HOSTILE,  # stages forced climax extensions on targets
    SexualDrainEffect: HOSTILE,  # drains the target's pleasure into the caster
    SaturateSensitivityEffect: HOSTILE,  # pins the target's sensitivity at the top
    ClampShameEffect: HOSTILE,  # pins the target's shame at the ceiling
    MarkSubmissionEffect: HOSTILE,  # marks the target permanently submissive
    RestorePurityEffect: BENEFICIAL,  # restores the target's virgin flag
    StimulusEffect: HOSTILE,  # sexual stimulus (an actor-only recipient never counts)
    PleasurePeakEffect: NEUTRAL,  # actor-bound peak effect
}


def _loaded_buff_polarity(buff_key: str) -> str:
    """Return one buff definition's polarity without importing ``world.rules``."""
    rules_buffs = sys.modules.get("world.rules.buffs")
    definitions = getattr(rules_buffs, "BUFF_DEFINITIONS", None)
    if definitions is not None:
        return str(definitions[buff_key].polarity)
    import yaml

    path = Path(__file__).parent.parent.parent / "rules" / "rulebook" / "buffs.yaml"
    for entry in yaml.safe_load(path.read_text(encoding="utf-8")) or ():
        if isinstance(entry, dict) and entry.get("key") == buff_key:
            return str(entry.get("polarity", "buff"))
    raise KeyError(buff_key)


def effect_target_polarity(
    effect: Any, buff_polarity: Callable[[str], str] | None = None
) -> str:
    """Resolve one parsed effect to ``hostile``, ``beneficial``, or ``neutral``.

    Raises ``KeyError`` for an unclassified effect kind (fail closed).
    """
    kind = EFFECT_TARGET_POLARITY[type(effect)]
    if kind == BUFF_DEFINITION:
        lookup = buff_polarity or _loaded_buff_polarity
        return HOSTILE if lookup(effect.buff_key) == "debuff" else BENEFICIAL
    if kind == GAUGE_DIRECTION:
        return HOSTILE if effect.direction == "drain" else BENEFICIAL
    return kind


def skill_target_polarity(
    skill: Any, buff_polarity: Callable[[str], str] | None = None
) -> tuple[bool, bool]:
    """Return ``(hostile, beneficial)`` for the effects routed to chosen targets.

    An effect counts only when its policy audience is ``SELECTED`` and its
    parsed recipient is not actor-bound; ``SkillDef`` normalizes
    ``effect_policies`` to one policy per parsed effect.
    """
    hostile = False
    beneficial = False
    for effect, policy in zip(skill.parsed_effects, skill.effect_policies, strict=True):
        if policy.audience is not EffectAudience.SELECTED:
            continue
        if isinstance(effect, StimulusEffect) and effect.recipient == "actor":
            continue
        polarity = effect_target_polarity(effect, buff_polarity)
        hostile = hostile or polarity == HOSTILE
        beneficial = beneficial or polarity == BENEFICIAL
    return hostile, beneficial


__all__ = [
    "BENEFICIAL",
    "BUFF_DEFINITION",
    "EFFECT_TARGET_POLARITY",
    "GAUGE_DIRECTION",
    "HOSTILE",
    "NEUTRAL",
    "POLARITY_CLASSES",
    "effect_target_polarity",
    "skill_target_polarity",
]
