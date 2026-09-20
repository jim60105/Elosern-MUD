"""Registry data slice: the 雷 elemental spell tree.

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
        # 雷 — 學徒（先制路線・根）
        _spell(
            "static_ward",
            "靜電護罩",
            "以靜電護罩，隨時反擊近身之敵。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=10,
            element="lightning",
            effects=("self_buff_apply:lightning_static_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            effect_policies=(EffectPolicy(),),
        ),
        # 雷 — 術師（先制路線）
        _spell(
            "lightning_flicker",
            "雷光連閃",
            "雷光連閃，使自身行動順序提前並提升麻痺微階觸發率。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=22,
            element="lightning",
            effects=(
                "self_buff_apply:lightning_flicker_ward",
                "self_buff_apply:flicker_advance",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("static_ward", 3),),
            effect_policies=(EffectPolicy(), EffectPolicy()),
        ),
        # 雷 — 大師（先制路線・分支點）
        _spell(
            "thunder_combo",
            "雷霆連擊",
            "以雷霆之勢連續攻擊，對單一目標造成多段魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=46,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("lightning_flicker", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(extra_strikes=2),
                ),
            ),
        ),
        # 雷 — 賢者（先制路線）
        _spell(
            "thunder_gods_haste",
            "雷神之速",
            "獲得雷神之速，追加行動機會。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=68,
            element="lightning",
            effects=("self_buff_apply:lightning_extra_action",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_combo", 5),),
            effect_policies=(EffectPolicy(),),
        ),
        # 雷 — 賢者（先制路線・分支終點）
        _spell(
            "thunder_shatter_strike",
            "碎雷連擊",
            "將雷霆連擊技巧磨練至極致，對單一目標造成高額魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_combo", 5),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 雷 — 主宰（先制路線・處決級）
        _spell(
            "judgement_thunder",
            "審判雷霆",
            "喚起審判雷霆，無視防禦對單一目標造成處決級魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("thunder_gods_haste", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 雷 — 學徒（過載路線・根）
        _spell(
            "spark_shock",
            "電擊術",
            "凝聚雷之魔力電擊，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=13,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 雷 — 術師（過載路線・分支點）
        _spell(
            "chain_lightning",
            "雷鎖術",
            "釋放連鎖閃電，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=27,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("spark_shock", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 雷 — 術師（過載路線・分支點）
        _spell(
            "paralyzing_bolt",
            "麻痺電擊",
            "射出麻痺電擊，對單一目標造成魔法傷害並使其麻痺。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="lightning",
            effects=("damage:lightning:magic", "buff_apply:paralysis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("spark_shock", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
            ),
        ),
        # 雷 — 大師（過載路線）
        _spell(
            "lightning_strike",
            "落雷術",
            "召喚落雷，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("chain_lightning", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 雷 — 大師（過載路線・分支終點）
        _spell(
            "thunder_prison",
            "雷獄囚縛",
            "引雷凝聚成獄囚縛目標，造成魔法傷害並附加強化版麻痺。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="lightning",
            effects=("damage:lightning:magic", "buff_apply:paralysis_enhanced"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("paralyzing_bolt", 3),),
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(),
            ),
        ),
        # 雷 — 賢者（過載路線）
        _spell(
            "heavens_thunder",
            "天雷降臨",
            "召喚天雷降臨，對範圍內所有目標造成極高魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=92,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("lightning_strike", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 雷 — 主宰（過載路線・毀滅級）
        _spell(
            "divine_lightning_slaughter",
            "神雷滅殺",
            "召喚神雷滅殺一切，對範圍內所有敵人造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=155,
            element="lightning",
            effects=("damage:lightning:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(SkillPrerequisite("heavens_thunder", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 雷 — 神格（兩線匯合・樹冠）
        _spell(
            "thunder_apotheosis",
            "雷霆神格",
            "化身雷霆神格，對範圍內所有敵人造成毀滅級魔法傷害，並將受擊目標當輪行動順序推至最後。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="lightning",
            effects=(
                "damage:lightning:magic",
                "buff_apply:apotheosis_retreat",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(
                SkillPrerequisite("judgement_thunder", 10),
                SkillPrerequisite("divine_lightning_slaughter", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
)
