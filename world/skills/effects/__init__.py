"""Typed effect-ID parsing for skill definitions.

Every effect prefix `SKILL_REGISTRY` may declare maps to exactly one frozen
dataclass here. `parse_effect` is the single dispatch point: consumers read
`SkillDef.parsed_effects` (typed instances) instead of re-splitting the raw
string, and an unrecognized prefix raises at registry-load time rather than
silently doing nothing at use time.

The package splits the historical single module into cohesive submodules
while preserving its full public surface:

- :mod:`world.skills.effects.passives` — the ownership/passive family,
  the ``EffectAudience`` vocabulary, and ``_known_buff_keys``
  (rulebook-only; never imports world.rules).
- :mod:`world.skills.effects.sexual` — the sexual event/act effect family.
- :mod:`world.skills.effects.combat` — the combat/cleanse/heal/gauge
  effect family.
- :mod:`world.skills.effects.policies` — the immutable policy, magnitude,
  and resolved-effect records.
- :mod:`world.skills.effects.parser` — ``parse_effect`` and its helpers.
"""

# Historical pass-through imports the old flat module leaked into its
# namespace; kept so ``vars(world.skills.effects)``-style surface parity
# holds for structural scans.
from dataclasses import dataclass  # noqa: F401
from enum import StrEnum  # noqa: F401
from math import isfinite  # noqa: F401
from collections.abc import Iterable, Mapping, Sequence  # noqa: F401
from typing import Any, Literal  # noqa: F401

from world.lore.elements import ELEMENT_REGISTRY  # noqa: F401
from world.skills.effects.combat import (  # noqa: F401
    CleanseEffect,
    DamageEffect,
    DisengageEffect,
    GaugeTransferEffect,
    HealEffect,
    SelfHealEffect,
)
from world.skills.effects.passives import (  # noqa: F401
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
    _known_buff_keys,
)
from world.skills.effects.parser import (  # noqa: F401
    parse_effect,
    _parse_bare,
    _parse_single_arg,
    _parse_stat_like,
)
from world.skills.effects.policies import (  # noqa: F401
    DamagePolicy,
    EffectPolicy,
    GaugeTransferPolicy,
    InteractionPolicy,
    ResolvedEffect,
    StateMagnitude,
    StateMagnitudeSubject,
    _SUPPORTED_MAGNITUDE_FIELDS,
)
from world.skills.effects.sexual import (  # noqa: F401
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
