"""Registry data slice: the 水 elemental spell tree.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
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
        # 水 — 學徒（潮汐路線）
        _spell(
            "tide_pull",
            "潮引術",
            "引動魔力潮汐，命中使目標魔力流失並回收其中一半至施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=11,
            element="water",
            effects=("gauge_transfer:mp:drain:fixed:5",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            effect_policies=(
                EffectPolicy(
                    transfer=GaugeTransferPolicy(caster_recovery_share=0.5),
                ),
            ),
        ),
        # 水 — 術師（潮汐路線）
        _spell(
            "ebbing_blight",
            "潮退侵蝕",
            "喚起退潮之蝕，對單一目標造成魔法傷害並附加潮退，持續造成魔力流失。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="water",
            effects=("damage:water:magic", "buff_apply:ebbing"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("tide_pull", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.0),
                EffectPolicy(),
            ),
        ),
        _spell(
            "water_shield",
            "水膜護身",
            "凝聚水膜護身，受擊時以魔力代扣傷害。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.SELF_ONLY,
            mp=22,
            element="water",
            effects=("self_buff_apply:water_film",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ebbing_blight", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        # 水 — 大師（潮汐路線）
        _spell(
            "ring_of_reflux",
            "回流之環",
            "引導魔力回流，恢復單一目標魔力，並依施法者身上的潮退標記獲得額外加值。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=42,
            element="water",
            effects=("gauge_transfer:mp:restore:fixed:40",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ebbing_blight", 3),),
            effect_policies=(
                EffectPolicy(
                    transfer=GaugeTransferPolicy(
                        restore_bonus_per_stack=(
                            ("ebbing", 10),
                            ("ebbing_deep", 10),
                            ("ebbing_maelstrom", 10),
                        ),
                    ),
                ),
            ),
        ),
        # 水 — 賢者（潮汐路線）
        _spell(
            "drowned_surging",
            "溺潮",
            "引發溺滅魔潮，使目標魔力加速流失，魔力歸零時陷入窒息；對魔力上限為零者改為造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=78,
            element="water",
            effects=("buff_apply:ebbing_maelstrom", "damage:water:magic"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ring_of_reflux", 5),),
            effect_policies=(
                EffectPolicy(),
                EffectPolicy(audience_condition="mp_max_zero"),
            ),
        ),
        # 水 — 主宰（潮汐路線）
        _spell(
            "sigil_of_the_barren_sea",
            "枯海之印",
            "施加枯海之印，對單一目標造成處決級魔法傷害，移除全部魔力並封鎖其恢復。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="water",
            effects=(
                "damage:water:magic",
                "gauge_transfer:mp:drain:all",
                "buff_apply:mp_regen_lock",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("drowned_surging", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 水 — 賢者（潮汐路線・範圍友方）
        _spell(
            "abyssal_surge",
            "深淵潮汛",
            "引動深淵魔潮，恢復我方全體魔力並附著回流狀態。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=82,
            element="water",
            effects=("gauge_transfer:mp:restore:fixed:25", "buff_apply:mana_reflux"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("ring_of_reflux", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ALLIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
        # 水 — 學徒（深海路線）
        _spell(
            "water_bolt",
            "水箭術",
            "凝聚水之魔力化為箭矢，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 水 — 術師（深海路線）
        _spell(
            "deep_current_spike",
            "深流刺",
            "凝聚深層暗流化為尖刺，對單一目標造成魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=24,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("water_bolt", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 水 — 大師（深海路線）
        _spell(
            "abyssal_whirlpool",
            "深海漩渦",
            "召喚深海漩渦，對範圍內所有目標造成魔法傷害、附加潮退並束縛其行動。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="water",
            effects=(
                "damage:water:magic",
                "buff_apply:ebbing_deep",
                "buff_apply:water_bind",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("deep_current_spike", 3),),
            effect_policies=(
                EffectPolicy(coefficient=1.4),
                EffectPolicy(),
                EffectPolicy(),
            ),
        ),
        # 水 — 賢者（深海路線）
        _spell(
            "abyssal_maw",
            "深淵巨口",
            "張開如深淵般的巨口，對單一目標造成魔法傷害，並吸取其現有魔力的兩成轉入施法者。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="water",
            effects=("damage:water:magic", "gauge_transfer:mp:drain:fraction:0.2"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("abyssal_whirlpool", 5),),
            effect_policies=(
                EffectPolicy(coefficient=2.8),
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=1.0)),
            ),
        ),
        # 水 — 賢者（深海路線）
        _spell(
            "tsunami",
            "海嘯術",
            "喚起滔天海嘯，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=95,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("abyssal_whirlpool", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 水 — 主宰（深海路線）
        _spell(
            "abyssal_tide",
            "深淵巨潮",
            "召喚深淵巨潮，對範圍內所有目標造成毀滅級魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=145,
            element="water",
            effects=("damage:water:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(SkillPrerequisite("tsunami", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 水 — 神格（兩線匯合）
        _spell(
            "abyssal_heart",
            "深海神格",
            "神格之潮降臨，抽乾敵方全體魔力並造成毀滅級魔法傷害，同時將魔力全量歸還我方全體。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=230,
            element="water",
            effects=(
                "damage:water:magic",
                "gauge_transfer:mp:drain:all",
                "gauge_transfer:mp:restore:fixed:25",
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(
                SkillPrerequisite("sigil_of_the_barren_sea", 10),
                SkillPrerequisite("abyssal_tide", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
)
