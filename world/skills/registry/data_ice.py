"""Registry data slice: the 冰 elemental spell tree.

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
    SkillCategory,
    SkillDef,
    SkillPrerequisite,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
        # 冰 — 學徒（遲緩路線・根）
        _spell(
            "frost_breath",
            "凍結之息",
            "吐出極寒凍氣，使目標陷入遲緩。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="ice",
            effects=("buff_apply:ice_slow",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
        ),
        # 冰 — 術師（遲緩路線・分支點）
        _spell(
            "ice_wall",
            "冰牆術",
            "築起冰霜之牆，於目標周邊結霜成牆並對進出者附加遲緩。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=25,
            element="ice",
            effects=("buff_apply:ice_wall_frost", "buff_apply:ice_slow"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("frost_breath", 3),),
        ),
        # 冰 — 大師（遲緩路線・泥沼分支終點）
        _spell(
            "frost_mire",
            "凝霜泥沼",
            "使範圍地面霜化成泥沼，使停留在其上的敵人大幅降低敏捷。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="ice",
            effects=("buff_apply:ice_frost_mire",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_wall", 3),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
        ),
        # 冰 — 大師（遲緩路線・永凍分支）
        _spell(
            "permafrost_domain",
            "永凍領域",
            "展開永凍領域，使範圍內所有目標陷入凍結無法行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="ice",
            effects=("buff_apply:ice_freeze",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_wall", 3),),
        ),
        # 冰 — 賢者（遲緩路線・永凍分支）
        _spell(
            "absolute_tundra",
            "絕對凍土",
            "將大地化為絕對凍土，對範圍內所有敵人造成魔法傷害並使其凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=82,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_tundra"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("permafrost_domain", 8),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 冰 — 主宰（遲緩路線・永凍分支終點・毀滅級）
        _spell(
            "eternal_ice_field",
            "長夜冰原",
            "展開無盡長夜的極寒冰原，對範圍內所有敵人造成毀滅級魔法傷害並附加凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=158,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_nightfall"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("absolute_tundra", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 冰 — 學徒（監禁路線・根）
        _spell(
            "ice_shard",
            "冰錐術",
            "凝聚冰之魔力化為銳利冰錐，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=13,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 冰 — 術師（監禁路線）
        _spell(
            "frost_arrow_rain",
            "冷凍箭雨",
            "降下銳利冷凍箭雨，對範圍內所有敵人造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=28,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_shard", 3),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.0),
            ),
        ),
        # 冰 — 大師（監禁路線・分支點）
        _spell(
            "ice_prison",
            "冰封監牢",
            "以寒冰凝成監牢，對單一目標施加定身封鎖其行動。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="ice",
            effects=("buff_apply:ice_prison",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("frost_arrow_rain", 3),),
        ),
        # 冰 — 賢者（監禁路線・暴風分支）
        _spell(
            "blizzard",
            "暴風雪",
            "喚起狂暴暴風雪，對範圍內所有敵人造成高額魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=88,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_prison", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
            ),
        ),
        # 冰 — 賢者（監禁路線・碎裂分支終點）
        _spell(
            "crystal_shatter",
            "冰晶爆裂",
            "引爆目標身上的冰霜碎屑，對凍結或定身狀態的目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="ice",
            effects=("damage:ice:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("ice_prison", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(
                        predicate=(
                            "buff:ice_freeze",
                            "buff:ice_freeze_tundra",
                            "buff:ice_freeze_nightfall",
                            "buff:ice_freeze_apotheosis",
                            "buff:ice_prison",
                        ),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 冰 — 主宰（監禁路線・暴風分支終點・處決級）
        _spell(
            "absolute_zero",
            "絕對零度",
            "釋放極致寒氣，對單一目標造成無視防禦的處決級魔法傷害並附加凍結。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=140,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_nightfall"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(SkillPrerequisite("blizzard", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
                EffectPolicy(),
            ),
        ),
        # 冰 — 神格（兩線匯合・樹冠・毀滅級）
        _spell(
            "eternal_frost_apotheosis",
            "永凍神格",
            "顯現永凍神格，對範圍內所有敵人造成毀滅級魔法傷害並附加超長凍結。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=225,
            element="ice",
            effects=("damage:ice:magic", "buff_apply:ice_freeze_apotheosis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(
                SkillPrerequisite("eternal_ice_field", 10),
                SkillPrerequisite("absolute_zero", 10),
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
