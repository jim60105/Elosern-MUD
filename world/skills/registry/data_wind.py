"""Registry data slice: the 風 elemental spell tree (incl. the flight passive).

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
        # 風 — 學徒（機動路線・根）
        _spell(
            "gale_step",
            "疾風術",
            "以疾風強化自身，提升速度。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=10,
            element="wind",
            effects=("self_buff_apply:gale_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
        ),
        # 風 — 術師（機動路線）
        _spell(
            "gale_chain_step",
            "疾風連步",
            "進一步提升身法流暢度，在移動中積蓄速度。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=20,
            element="wind",
            effects=("self_buff_apply:gale_chain_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_step", 3),),
        ),
        # 風 — 大師（機動路線）
        _spell(
            "afterimage_step",
            "神速殘影",
            "速度突破常規拉出殘影，大幅提升閃避但犧牲攻擊精準。",
            TargetSpec.SELF,
            usable_out_of_combat=True,
            mp=45,
            element="wind",
            effects=("self_buff_apply:afterimage_step_haste",),
            faction_constraint=FactionConstraint.SELF_ONLY,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_chain_step", 3),),
        ),
        # 風 — 賢者（機動路線・終點）
        _spell(
            "haste_domain",
            "神速領域",
            "展開神速領域，大幅提升領域內全體同伴的速度與迴避。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=70,
            element="wind",
            effects=("buff_apply:haste_domain_haste",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("afterimage_step", 5),),
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        ),
        # 風 — 學徒（破壞路線・根）
        _spell(
            "wind_blade",
            "風刃術",
            "颳起銳利風刃，對範圍內所有目標造成魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=14,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            effect_policies=(EffectPolicy(coefficient=0.7),),
        ),
        # 風 — 術師（破壞路線・分支點）
        _spell(
            "tornado_blade",
            "龍捲風刃",
            "捲起龍捲風刃，對單一目標造成高額魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=26,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("wind_blade", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 風 — 大師（破壞路線・暴風分支）
        _spell(
            "storm_domain",
            "暴風領域",
            "展開暴風領域，對範圍內所有敵人造成魔法傷害並擊退敵人。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=50,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("tornado_blade", 3),),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.4),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 風 — 大師（破壞路線・刃舞分支）
        _spell(
            "gale_dance_strike",
            "疾風刃舞",
            "以疾風之勢舞動刃擊，對單一目標造成連續兩次魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=40,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("tornado_blade", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.0,
                    damage=DamagePolicy(extra_strikes=1),
                ),
            ),
        ),
        # 風 — 賢者（破壞路線・暴風分支）
        _spell(
            "heavens_wrath_storm",
            "天譴風暴",
            "喚起天譴風暴，對範圍內所有目標造成極高魔法傷害。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=90,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("storm_domain", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 風 — 賢者（破壞路線・刃舞分支）
        _spell(
            "sky_rending_slash",
            "天穹裂斬",
            "聚風成刃撕裂天穹，對單一目標造成極高魔法傷害。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=80,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("gale_dance_strike", 8),),
            effect_policies=(EffectPolicy(coefficient=2.8),),
        ),
        # 風 — 主宰（破壞路線・暴風分支終點）
        _spell(
            "sky_tempest",
            "蒼穹暴風",
            "召喚蒼穹暴風，對範圍內所有敵人造成毀滅級魔法傷害並附加擊退控制。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=150,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced_tempest"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("heavens_wrath_storm", 8),),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        ),
        # 風 — 主宰（破壞路線・刃舞分支終點・處決級）
        _spell(
            "vacuum_severance",
            "真空斬滅",
            "斬出真空之刃，對單一目標造成處決級魔法傷害（無視防禦）。",
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            mp=130,
            element="wind",
            effects=("damage:wind:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(SkillPrerequisite("sky_rending_slash", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 風 — 神格（兩線匯合・樹冠）
        _spell(
            "sky_apotheosis",
            "天穹神格",
            "展現天穹神格，對範圍內所有敵人造成毀滅級魔法傷害並附加擊退控制 90 秒。",
            TargetSpec.AREA,
            usable_out_of_combat=True,
            mp=220,
            element="wind",
            effects=("damage:wind:magic", "buff_apply:displaced_apotheosis"),
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(
                SkillPrerequisite("sky_tempest", 10),
                SkillPrerequisite("vacuum_severance", 10),
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
        _skill(
            "flight",
            "飛行術",
            "操控風元素飛行，可前往遠處的場合。",
            SkillKind.PASSIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            element="wind",
            effects=["movement:flight"],
            category=SkillCategory.ENHANCEMENT,
            group="身法",
        ),
)
