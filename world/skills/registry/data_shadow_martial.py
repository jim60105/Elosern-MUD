"""Registry data slice: the 影流刀術 martial-arts tree.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    DamagePolicy,
    EffectPolicy,
)

from world.skills.cast_conditions import (
    CastCondition,
    CastConditionSubject,
)

from world.skills.registry.builders import (
    _skill,
)

from world.skills.registry.vocab import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
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
        # 影流刀術 — 根（martial-arts-catalog D1/D3：outsiders 從此節起步，不設架式門檻）
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
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 影流刀術 — 分支點（雙持劍術架式門檻，martial-arts-catalog D3）
        _skill(
            "phantom_dance",
            "幻影連斬",
            "以幻影般的身法連斬兩次，對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 24},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("shadow_slash", 3),),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"skill_owned": "dual_wield_style"}),
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(extra_strikes=1),
                ),
            ),
        ),
        # 影流刀術 — 分支終點（dual_blade_mastery 的重新鍵入，martial-arts-catalog D4）
        _skill(
            "dual_blade_waltz",
            "雙刃旋舞",
            "以旋舞般的雙刃連擊，對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 30},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("phantom_dance", 5),),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"skill_owned": "dual_wield_style"}),
            ),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 影流刀術 — 分支終點
        _skill(
            "shadow_veil_execution",
            "暗影獵殺",
            "潛入影障狙殺目標要害，對單一目標造成物理傷害並留下暗影創傷。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 28},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical", "buff_apply:shadow_wound"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("phantom_dance", 5),),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"skill_owned": "dual_wield_style"}),
            ),
            effect_policies=(
                EffectPolicy(coefficient=2.8),
                EffectPolicy(),
            ),
        ),
        # 影流刀術 — 兩線匯合（樹冠，martial-arts-catalog D1）
        _skill(
            "shadow_dance_finale",
            "暗影終劍",
            "影流刀術之終劍，無視防禦對單一目標造成毀滅級物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 44},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(
                SkillPrerequisite("dual_blade_waltz", 10),
                SkillPrerequisite("shadow_veil_execution", 10),
            ),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"skill_owned": "dual_wield_style"}),
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.5,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
)
