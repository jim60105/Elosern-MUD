"""Registry data slice: the 火 elemental spell tree.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
)

from world.skills.registry.builders import (
    _spell,
)

from world.skills.registry.vocab import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillPrerequisite,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
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
)
