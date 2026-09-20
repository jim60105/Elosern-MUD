"""Registry data slice: the 暗 elemental spell tree.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    DamagePolicy,
    EffectPolicy,
)

from world.skills.registry.builders import (
    _spell,
)

from world.skills.registry.vocab import (
    SkillCategory,
    SkillDef,
    SkillPrerequisite,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
        # 暗 — 學徒（詛咒路線・根）
        _spell(
            "weaken",
            "衰弱術",
            "施展衰弱術，降低單一目標的攻擊力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="dark",
            effects=("buff_apply:dark_weaken",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 術師（詛咒路線・分支點）
        _spell(
            "curse",
            "詛咒術",
            "施展詛咒術，削弱單一目標的攻擊、防禦與敏捷。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=26,
            element="dark",
            effects=("buff_apply:dark_curse",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("weaken", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 大師（詛咒路線・純減益分支）
        _spell(
            "curse_spread",
            "詛咒擴散",
            "擴散詛咒之力，削弱範圍內全體目標的攻擊與防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="dark",
            effects=("buff_apply:dark_spread",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 賢者（詛咒路線・控場分支終點）
        _spell(
            "dark_dominion",
            "黑暗支配",
            "展開黑暗支配，使範圍內所有目標陷入恐懼無法行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=72,
            element="dark",
            effects=("buff_apply:fear",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse_spread", 5),),
            effect_policies=(EffectPolicy(),),
        ),
        # 暗 — 大師（詛咒路線・侵蝕分支）
        _spell(
            "shadow_torture",
            "暗影之刑",
            "對單一目標施以暗影之刑，造成高額魔法傷害並附著侵蝕，流失全額轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=41,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("curse", 3),),
            effect_policies=(EffectPolicy(coefficient=2.0), EffectPolicy()),
        ),
        # 暗 — 賢者（詛咒路線・深層侵蝕）
        _spell(
            "shadow_blight",
            "暗影侵蝕",
            "注入深層暗影侵蝕，造成巨量魔法傷害並附著深層侵蝕，流失全額轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion_deep"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_torture", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8), EffectPolicy()),
        ),
        # 暗 — 主宰（詛咒路線・處決匯合支）
        _spell(
            "underworld_judgment",
            "冥界審判",
            "喚起冥界審判，對單一目標造成處決級魔法傷害，無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_blight", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 暗 — 學徒（吞噬路線・根）
        _spell(
            "shadow_bolt",
            "暗影箭",
            "射出暗影之箭，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=14,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 暗 — 術師（吞噬路線）
        _spell(
            "dark_burst",
            "闇裂術",
            "釋放闇之爆裂，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=29,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("shadow_bolt", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 暗 — 大師（吞噬路線）
        _spell(
            "dark_corrosion_domain",
            "闇蝕領域",
            "展開闇蝕領域，對範圍內所有目標造成魔法傷害並附著侵蝕，受蝕者流失全額轉入施法者。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=47,
            element="dark",
            effects=("damage:dark:magic", "buff_apply:dark_corrosion"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("dark_burst", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4), EffectPolicy()),
        ),
        # 暗 — 賢者（吞噬路線・處決）
        _spell(
            "abyss_devour",
            "深淵吞噬",
            "召喚深淵吞噬目標，對單一目標造成處決級魔法傷害，無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=85,
            element="dark",
            effects=("damage:dark:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("dark_corrosion_domain", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 暗 — 主宰（吞噬路線・毀滅＋自癒）
        _spell(
            "void_annihilation",
            "虛空湮滅",
            "召喚湮滅萬物的虛空，對範圍內所有目標造成毀滅級魔法傷害，並命中回復施法者已損 HP 的 10%。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=155,
            element="dark",
            effects=("damage:dark:magic", "self_heal:missing_fraction:0.1"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(SkillPrerequisite("abyss_devour", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(),
            ),
        ),
        # 暗 — 神格（兩根匯合頂點・樹冠）
        _spell(
            "abyssal_apotheosis",
            "深淵神格",
            "展現深淵終極神格，對範圍內所有目標造成毀滅級魔法傷害，施加巨幅削弱，並命中回復施法者已損 HP 的 15%。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="dark",
            effects=(
                "damage:dark:magic",
                "buff_apply:dark_apotheosis",
                "self_heal:missing_fraction:0.15",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(
                SkillPrerequisite("underworld_judgment", 10),
                SkillPrerequisite("void_annihilation", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
)
