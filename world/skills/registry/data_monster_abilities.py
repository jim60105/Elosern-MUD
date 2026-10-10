"""Registry data slice: authored monster resource abilities.

Declared separately from character skill trees (design §3.1, §5.1).
The crocodile contact-drain ability is assembled into SKILL_REGISTRY
with monster identity eligibility and water physical damage with
hit-dependent fixed MP drain. The sparrow contact ability is assembled the
same way with wind physical damage plus a hit-dependent accuracy debuff.
The crab contact ability is assembled the same way with light physical damage
plus a self-mounted defense guard granted by every resolved attempt.
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
    _skill(
        "lamp_carapace_claw",
        "燈甲螯擊",
        "以螯足夾擊單一敵方目標，造成物理傷害；出擊時收緊甲殼，短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # True for every monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile and sparrow declare).
        usable_out_of_combat=True,
        element="light",
        effects=["damage:light:physical", "self_buff_apply:lamp_carapace_guard"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="light",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("tide_lamp_crab",),
        ),
        prerequisites=(),
        effect_policies=(
            # Occurrence 0 is the ordinary enemy strike.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            # Occurrence 1 binds the caster with no hit dependency: the guard is
            # part of an affordable, target-resolved attempt, including a miss.
            # A source-enemy-hit dependency would intersect the SELF audience
            # away from the actor (see world/rules/action/routing.py), so this
            # self mount deliberately declares none.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
)
