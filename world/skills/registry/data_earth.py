"""Registry data slice: the 土 elemental spell tree (incl. the self-only hardened_skin row).

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
    _skill,
    _spell,
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
        # 土 — 學徒（地形路線・根）
        _spell(
            "stone_shard",
            "石礫術",
            "凝聚土之魔力擲出石礫，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 土 — 術師（護甲路線）
        _spell(
            "stone_armor",
            "岩甲術",
            "以岩石覆蓋目標形成岩甲，提升防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="earth",
            effects=("buff_apply:earth_stone_armor",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("hardened_skin", 3),),
        ),
        # 土 — 大師（護甲路線・磐石）
        _spell(
            "bedrock_bastion",
            "磐石壁壘",
            "召出磐石壁壘，提升我方全體防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="earth",
            effects=("buff_apply:earth_bedrock",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("stone_armor", 3),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 土 — 賢者（護甲路線・磐石）
        _spell(
            "earthen_ward",
            "大地庇護",
            "以大地之力庇護我方，提升我方全體防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=75,
            element="earth",
            effects=("buff_apply:earth_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("bedrock_bastion", 5),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 土 — 大師（護甲路線・荊棘）
        # thorned_carapace is inherently self-only (`self_buff_apply`); the
        # counter itself is reaction data — earth_carapace is the mount the
        # shipped physical_hit rule's buff_active gate keys off.
        _spell(
            "thorned_carapace",
            "荊棘反甲",
            "覆上荊棘反甲，受到物理攻擊時反彈傷害。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=40,
            element="earth",
            effects=("self_buff_apply:earth_carapace",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            faction_constraint=FactionConstraint.SELF_ONLY,
            prerequisites=(SkillPrerequisite("stone_armor", 3),),
        ),
        # 土 — 術師（地形路線）
        _spell(
            "dust_veil",
            "沙塵術",
            "捲起漫天沙塵，降低範圍內所有目標的命中。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=22,
            element="earth",
            effects=("buff_apply:earth_dust_veil",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("stone_shard", 3),),
        ),
        # 土 — 大師（地形路線・裂縫）
        _spell(
            "ground_fissure",
            "地裂術",
            "地面裂開成縫，留在裂縫上的目標持續承受地形傷害並陷入遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=42,
            element="earth",
            effects=("buff_apply:earth_fissure", "buff_apply:ice_slow"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("dust_veil", 3),),
        ),
        # 土 — 大師（地形路線・崩落）
        _spell(
            "rockslide",
            "岩壁崩落",
            "使岩壁崩落碾壓目標，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=48,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("dust_veil", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 土 — 賢者（地形路線・裂縫）
        _spell(
            "earthquake",
            "地震術",
            "撼動大地引發地震，對範圍內所有目標造成魔法傷害，並附加裂縫地形標記與遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="earth",
            effects=(
                "damage:earth:magic",
                "buff_apply:earth_fissure_quake",
                "buff_apply:ice_slow",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("ground_fissure", 5),),
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 土 — 賢者（地形路線・單體）
        _spell(
            "fault_rupture",
            "地脈崩裂",
            "撕裂地脈撼動目標根基，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("rockslide", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 土 — 主宰（地形路線・裂縫）
        _spell(
            "mountain_collapse",
            "山嶽崩落",
            "令山嶽崩落壓垮一切，對範圍內所有目標造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("earthquake", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 土 — 主宰（地形路線・單體）
        # 處決級（無視防禦）+ 裂縫連動：站在任一裂縫標記上觸發一次
        # 1.15 乘算（4.0×1.15=4.6 == 4.0+0.6，D6）；predicate any-match-once
        # 讓三個裂縫 rung 只計一次。
        _spell(
            "earths_judgment",
            "大地審判",
            "喚起大地審判之力，無視防禦對單一目標造成處決級魔法傷害；對站在裂縫上的目標額外加重。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="earth",
            effects=("damage:earth:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(SkillPrerequisite("fault_rupture", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(
                        predicate=(
                            "buff:earth_fissure",
                            "buff:earth_fissure_quake",
                            "buff:earth_fissure_apex",
                        ),
                        attack_multiplier=1.15,
                        unconditional_defense_bypass=True,
                    ),
                ),
            ),
        ),
        # 土 — 神格（兩線匯合）
        # 「覆蓋全場」：頂規裂縫標記與遲緩以 ENEMIES audience 施加於區域
        # 選擇的每個敵方目標（abyssal_heart 先例）。
        _spell(
            "earthen_apotheosis",
            "大地神格",
            "大地甦醒，對範圍內所有敵人造成毀滅級魔法傷害，並召出覆蓋全場的頂規裂縫地形，留在其上者持續承受地形傷害並陷入遲緩。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=220,
            element="earth",
            effects=(
                "damage:earth:magic",
                "buff_apply:earth_fissure_apex",
                "buff_apply:ice_slow",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(
                SkillPrerequisite("mountain_collapse", 10),
                SkillPrerequisite("earths_judgment", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 土 — 學徒
        # hardened_skin is inherently self-only (`self_buff_apply`), so it
        # declares SELF_ONLY — the `_elemental_spells` builder fixes ANY, so
        # this single entry is written out individually per the skill-registry
        # spec's self-only constraint.
        _skill(
            "hardened_skin",
            "硬化肌膚",
            "使自身肌膚硬化如岩，提升防禦。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            cost={"mp": 10},
            element="earth",
            faction_constraint=FactionConstraint.SELF_ONLY,
            effects=["self_buff_apply:earth_hardened_skin"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
        ),
)
