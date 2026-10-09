"""Registry data slice: authored monster resource abilities.

Declared separately from character skill trees (design §3.1, §5.1).
The crocodile contact-drain ability is assembled into SKILL_REGISTRY
with monster identity eligibility and water physical damage with
hit-dependent fixed MP drain.
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
)
