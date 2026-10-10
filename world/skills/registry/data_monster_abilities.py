"""Registry data slice: authored monster resource abilities.

Declared separately from character skill trees (design §3.1, §5.1).
The crocodile contact-drain ability is assembled into SKILL_REGISTRY
with monster identity eligibility and water physical damage with
hit-dependent fixed MP drain. The sparrow contact ability is assembled the
same way with wind physical damage plus a hit-dependent accuracy debuff.
"""

from world.skills.effects import (
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
)
from world.skills.registry.builders import _skill
from world.skills.registry.vocab import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillEligibility,
    SkillKind,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
    _skill(
        "tide_devouring_bite",
        "吞潮咬擊",
        "以水屬性力量纏繞咬合，對單一敵方目標造成物理傷害，並在命中時吸取其現有魔力轉入自身。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("tide_devouring_crocodile",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
                transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
            ),
        ),
    ),
    _skill(
        "grain_shaking_peck",
        "震穗啄擊",
        "以短促氣流啄擊單一敵方目標，造成物理傷害；命中後使對手短暫分心，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # True for both monster abilities: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile declares).
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "buff_apply:grain_rattle"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("sway_whistle_sparrow",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=0.8,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
)
