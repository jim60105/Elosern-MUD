"""Registry data slice: sword-line martial arts (``basic_attack`` through the 劍術 canopy).

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
            "basic_attack",
            "基本攻擊",
            "以普通攻擊對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
        ),
        # 劍術 — 見習（根，martial-arts-catalog D1）
        _skill(
            "basic_swordplay",
            "見習劍術",
            "以基礎劍術架式對單一目標揮出一記物理斬擊。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 8},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            effect_policies=(EffectPolicy(coefficient=1.0),),
        ),
        # 劍術 — 分支點（single-target execution chain and area destruction chain）
        _skill(
            "flowing_strikes",
            "順勢連斬",
            "順勢揮出連貫的劍勢，對單一目標造成連續兩次物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 16},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("basic_swordplay", 3),),
            effect_policies=(
                EffectPolicy(
                    coefficient=1.4,
                    damage=DamagePolicy(extra_strikes=1),
                ),
            ),
        ),
        # 劍術 — 單體執行分支
        _skill(
            "tendon_sever",
            "斷筋斬",
            "瞄準要害斬向對手筋腱，對單一目標造成物理傷害並使其斷筋。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 24},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical", "buff_apply:martial_hamstring"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("flowing_strikes", 3),),
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(),
            ),
        ),
        # 劍術 — 範圍破壞分支
        _skill(
            "whirlwind_slash",
            "迴旋斬",
            "揮劍迴旋一周，對範圍內所有目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            cost={"sp": 22},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("flowing_strikes", 3),),
            effect_policies=(EffectPolicy(coefficient=1.4),),
        ),
        # 劍術 — 單體執行分支
        _skill(
            "thousand_blade_art",
            "千刃連斬",
            "以千變萬化的劍勢連續斬擊，對單一目標造成三段物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 30},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("tendon_sever", 5),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(extra_strikes=2),
                ),
            ),
        ),
        # 劍術 — 範圍破壞分支
        _skill(
            "blade_storm",
            "劍刃風暴",
            "捲起劍刃形成的風暴，對範圍內所有目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            cost={"sp": 28},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("whirlwind_slash", 5),),
            effect_policies=(EffectPolicy(coefficient=2.0),),
        ),
        # 劍術 — 單體執行分支終點
        _skill(
            "blade_saint_arts",
            "劍聖斬",
            "以劍聖之技無視防禦斬出致命一劍，對單一目標造成高額物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 38},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("thousand_blade_art", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=4.0,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
            ),
        ),
        # 劍術 — 範圍破壞分支終點（devastation rung）
        _skill(
            "thousand_army_slash",
            "破軍斬",
            "斬勢如破千軍，對範圍內所有目標造成毀滅級物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            cost={"sp": 36},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(SkillPrerequisite("blade_storm", 8),),
            effect_policies=(
                EffectPolicy(
                    coefficient=2.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
            ),
        ),
        # 劍術 — 兩線匯合（樹冠，martial-arts-catalog D1）
        _skill(
            "true_sword_saint",
            "大劍豪",
            "劍術造詣臻至大劍豪之境，無視防禦對單一目標造成毀滅級物理傷害，並使自身進入劍豪之境。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            cost={"sp": 48},
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:none:physical", "self_buff_apply:sword_saint_domain"],
            category=SkillCategory.MARTIAL_ARTS,
            prerequisites=(
                SkillPrerequisite("blade_saint_arts", 10),
                SkillPrerequisite("thousand_army_slash", 10),
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=5.5,
                    damage=DamagePolicy(bypass_defense=True, predicate=()),
                ),
                EffectPolicy(),
            ),
        ),
)
