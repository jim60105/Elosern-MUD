"""Registry data slice: the 神之秘法 (DIVINE_MYSTERY) chains.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.effects import (
    EffectAudience,
    EffectPolicy,
)

from world.skills.registry.builders import (
    _skill,
)

from world.skills.registry.vocab import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
        # ------------------------------------------------------------------
        # 神之秘法 (DIVINE_MYSTERY): the three known chains plus the
        # three-parent convergence node, transcribed from the authored node
        # table (docs/lore/skill-trees/divine-mystery.md section 2).
        #
        # Every node is zero-cost, bloodline-gated and usable outside
        # combat. Grant scales and the party audience live in the
        # per-occurrence EffectPolicy (conferral-grant-store D4/D3), so the
        # category declares no damage or healing effect and derives no MP
        # cost band (spell_tier_for stays None for every member). Chain
        # depth is expressed by prerequisite edges and the derived tip cap.
        # ------------------------------------------------------------------
        # 統御線 — "power belongs to the one who earned it".
        _skill(
            "dominion_art",
            "統御術",
            "授予目標一部分自身技能的效果。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            # The lore prices this root at 一成 (0.10): the scale is the
            # per-occurrence coefficient the conferral handlers read, so the
            # shipped verb records grants at the priced strength from the
            # moment the mechanism becomes castable.
            effect_policies=(EffectPolicy(coefficient=0.1),),
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "dominion_recall",
            "權能收回",
            "解除目標身上的一切技能授予與成長授予，不論來源為何。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["revoke_grants"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("dominion_art", 3),),
        ),
        _skill(
            "shared_dominion",
            "共權統御",
            "把施法者持有的同一批可授予被動，一次覆蓋全隊。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            effect_policies=(
                EffectPolicy(coefficient=0.1, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("dominion_art", 3),),
        ),
        _skill(
            "sovereign_investiture",
            "王權授予",
            "以更高的授予強度，把施法者持有的可授予被動覆蓋全隊。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_skill_partial"],
            effect_policies=(
                EffectPolicy(coefficient=0.25, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("shared_dominion", 3),),
        ),
        # 傳承線 — "learning takes time".
        _skill(
            "mentors_covenant",
            "師徒契約",
            "把自身的學習節奏借給目標，加速其熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(EffectPolicy(coefficient=1.5),),
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "chorus_of_ages",
            "世代合誦",
            "把自身的學習節奏借給全隊，加速熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(
                EffectPolicy(coefficient=1.5, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("mentors_covenant", 3),),
        ),
        _skill(
            "undying_tutelage",
            "不朽教誨",
            "以近乎精靈的學習節奏覆蓋全隊，大幅加速熟練度累積。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["confer_growth_rate"],
            effect_policies=(
                EffectPolicy(coefficient=3.0, audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("chorus_of_ages", 3),),
        ),
        # 帷幕線 — "what you see is what is real".
        _skill(
            "status_disguise",
            "狀態偽裝",
            "以神之秘法偽裝自身的外貌與部分能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["set_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
        ),
        _skill(
            "bestowed_veil",
            "賜帷",
            "把帷幕蓋到目標身上，改寫其顯示層的外貌與能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["set_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("status_disguise", 3),),
        ),
        _skill(
            "true_name_sight",
            "真名之視",
            "清除目標身上任何來源的偽裝層。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["reveal_disguise"],
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(SkillPrerequisite("status_disguise", 5),),
        ),
        # 匯合 — the capstone waits for all three chain ends at Lv.10.
        _skill(
            "crown_apotheosis",
            "冠冕神格",
            "把三條秘法之鏈的極限同時授予全隊：授予力量、借出成長、蓋上帷幕。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=[
                "confer_skill_partial",
                "confer_growth_rate",
                "set_disguise",
            ],
            effect_policies=(
                EffectPolicy(coefficient=0.5, audience=EffectAudience.ALLIES),
                EffectPolicy(coefficient=5.0, audience=EffectAudience.ALLIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
            category=SkillCategory.DIVINE_MYSTERY,
            prerequisites=(
                SkillPrerequisite("sovereign_investiture", 10),
                SkillPrerequisite("undying_tutelage", 10),
                SkillPrerequisite("true_name_sight", 10),
            ),
        ),
)
