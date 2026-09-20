"""Registry data slice: the 光 elemental spell tree.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    InteractionPolicy,
    StateMagnitude,
    StateMagnitudeSubject,
)

from world.skills.cast_conditions import (
    CastCondition,
    CastConditionSubject,
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
        # 光 — 學徒
        _spell(
            "heal",
            "治癒術",
            "以光之魔力治癒，恢復單一目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=12,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        _spell(
            "light_arrow",
            "光箭術",
            "射出光之箭矢，對單一目標造成魔法傷害，對暗屬性或不死系目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=14,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            effect_policies=(
                EffectPolicy(
                    coefficient=1.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 光 — 術師
        _spell(
            "mass_heal",
            "群體治癒",
            "施展群體治癒，恢復範圍內所有目標的生命力。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=30,
            element="light",
            effects=("heal:area",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("heal", 3),),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        _spell(
            "purify",
            "淨化術",
            "以淨化之光，解除單一目標的異常狀態。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=22,
            element="light",
            effects=("cleanse:status",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("light_arrow", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        _spell(
            "penitent_touch",
            "懺悔之觸",
            "以懺悔之觸碰造成光魔法傷害，對近期有強迫行為之目標追加一次審判打擊。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=27,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("purify", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=1.4,
                    damage=DamagePolicy(
                        predicate=("undead",),
                        attack_multiplier=1.5,
                        repeat_when="forced_interaction",
                        extra_strikes=1,
                    ),
                ),
            ),
        ),
        # 光 — 大師
        _spell(
            "advanced_heal",
            "高級治癒",
            "施展高級治癒，大量恢復單一目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=46,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("mass_heal", 3),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        _spell(
            "sanctified_ward",
            "聖光庇護陣",
            "佈下聖光庇護陣，賦予範圍內所有目標持續回復生命力的庇護。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=45,
            element="light",
            effects=("buff_apply:sanctified_ward",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("advanced_heal", 3),),
            effect_policies=(EffectPolicy(),),
        ),
        _spell(
            "judgment_strike",
            "聖裁斬",
            "凝聚聖裁之力斬向目標，對暗屬性或不死系目標造成額外傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=44,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("penitent_touch", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.5,
                    ),
                ),
            ),
        ),
        # 光 — 賢者
        _spell(
            "revival_light",
            "復甦之光",
            "綻放復甦之光，大量恢復瀕危目標的生命力。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=82,
            element="light",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("advanced_heal", 5),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        _spell(
            "holy_radiance",
            "神聖光輝",
            "綻放神聖光輝，對敵方造成光魔法傷害，同時淨化自身與友方的異常狀態。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="light",
            effects=("damage:light:magic", "cleanse:status"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("judgment_strike", 5),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        ),
        # 光 — 主宰
        _spell(
            "goddess_blessing",
            "女神降福",
            "獲得女神的祝福，大量恢復範圍內所有目標的生命力並強化防禦。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="light",
            effects=("heal:area", "buff_apply:light_blessing"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("revival_light", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8), EffectPolicy()),
        ),
        _spell(
            "holy_kiss_heal",
            "聖吻之癒〔聖禮〕",
            "施展聖吻聖儀，雙方皆需處於微興奮以上，以興奮序數提升治癒威力並施加常規刺激。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="light",
            effects=("heal:single", "stimulus:both"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("revival_light", 8),),
            cast_conditions=(
                CastCondition(CastConditionSubject.ACTOR, {"field": "arousal", "gte": "微興奮"}),
                CastCondition(CastConditionSubject.EACH_TARGET, {"field": "arousal", "gte": "微興奮"}),
            ),
            interaction=InteractionPolicy(
                contact=True,
                distinct_participants=True,
                target_capable=False,
                resistible=True,
            ),
            effect_policies=(
                EffectPolicy(
                    magnitude=StateMagnitude(
                        subject=StateMagnitudeSubject.ACTOR,
                        field="arousal",
                        base=3.2,
                        per_ordinal=0.2,
                        maximum=4.0,
                        marker="climax_empowerment",
                    )
                ),
                EffectPolicy(),
            ),
        ),
        _spell(
            "goddess_milk",
            "女神之乳〔聖禮〕",
            "施展授乳聖儀，透過接觸儀式大量治療並淨化異常狀態，對目標施加依施法者有效露出加成的刺激。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=140,
            element="light",
            effects=("heal:single", "cleanse:status", "stimulus:target"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("holy_kiss_heal", 3),),
            interaction=InteractionPolicy(
                contact=True,
                distinct_participants=True,
                target_capable=True,
                resistible=True,
            ),
            effect_policies=(
                EffectPolicy(coefficient=2.8),
                EffectPolicy(),
                EffectPolicy(
                    stimulus_bonus=StateMagnitude(
                        subject=StateMagnitudeSubject.ACTOR,
                        field="effective_exposure",
                        base=0.0,
                        per_ordinal=2.0,
                        maximum=8.0,
                        marker="climax_empowerment",
                    )
                ),
            ),
        ),
        _spell(
            "blessed_climax",
            "天賜高潮〔聖禮〕",
            "施法者強行推進快感至極限並進入高潮期相，以超位階威力治療我方全體。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=170,
            element="light",
            effects=("heal:area", "pleasure_peak"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("goddess_milk", 5),),
            effect_policies=(
                EffectPolicy(coefficient=3.4),
                EffectPolicy(audience=EffectAudience.SELF),
            ),
        ),
        _spell(
            "heavens_judgment_light",
            "天啟聖裁",
            "喚起天啟聖裁，對單一目標造成毀滅級魔法傷害，對暗屬性或不死系無視防禦。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=135,
            element="light",
            effects=("damage:light:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(SkillPrerequisite("holy_radiance", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(
                        predicate=("dark", "undead"),
                        attack_multiplier=1.0,
                        bypass_defense=True,
                    ),
                ),
            ),
        ),
        # 光 — 神格
        _spell(
            "bliss_apotheosis",
            "至福神格",
            "神格之光降臨，治癒我方全體並重創敵方，附加目標最大生命值比例傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=240,
            element="light",
            effects=("heal:area", "damage:light:magic"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(
                SkillPrerequisite("blessed_climax", 10),
                SkillPrerequisite("heavens_judgment_light", 10),
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ALLIES, coefficient=3.8),
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.6,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
)
