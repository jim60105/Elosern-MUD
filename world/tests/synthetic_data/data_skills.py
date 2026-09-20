"""Skill-domain catalogs: skills, the paired sexual-act rows, and MP cost tiers.
"""

from __future__ import annotations

from world.lore.sexual_vocab import BODY_PARTS
from world.skills.cost_tiers import CostTier
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)
from world.skills.sexual_acts._builder import SexualActDef

from world.tests.synthetic_data.vocab import SYNTH_GLOWMIRE_ELEMENT, _SYNTH_ELEMENT

SYNTH_SKILLS: dict[str, SkillDef] = {
    "t_ember_burst": SkillDef(
        key="t_ember_burst",
        label="燼火爆發",
        description="將熾熱的燼屑化為爆裂的魔法波濤。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 12},
        usable_out_of_combat=True,
        element=_SYNTH_ELEMENT,
        effects=[f"damage:{_SYNTH_ELEMENT}:magic"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_SYNTH_ELEMENT,
    ),
    # Canopy spell consumed by the browser combat journey's first element
    # group (the shipped fire tree's deep/shallow shape): the deep cast
    # declares the shallow burst, so a fixture requesting only the deep
    # spell gets ``t_ember_burst`` closed in BEHIND it in ownership order.
    # Kept distinct from ``t_ember_burst`` itself, which the many kit probes
    # grant prereq-free.
    "t_ember_comet": SkillDef(
        key="t_ember_comet",
        label="燼流星",
        description="引燃天穹墜落的燼屑，轟擊單一目標。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 14},
        usable_out_of_combat=True,
        element=_SYNTH_ELEMENT,
        effects=[f"damage:{_SYNTH_ELEMENT}:magic"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_SYNTH_ELEMENT,
        prerequisites=(SkillPrerequisite("t_ember_burst", 3),),
    ),
    "t_hush_mend": SkillDef(
        key="t_hush_mend",
        label="靜謐癒合",
        description="以無聲的暖流癒合單一傷口的合成法術。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 11},
        usable_out_of_combat=True,
        element=_SYNTH_ELEMENT,
        effects=["heal:single"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_SYNTH_ELEMENT,
    ),
    "t_cinder_cleave": SkillDef(
        key="t_cinder_cleave",
        label="燼牙斬",
        description="揮出夾帶灼熱碎屑的物理斬擊。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=SkillCategory.MARTIAL_ARTS,
    ),
    "t_steady_stride": SkillDef(
        key="t_steady_stride",
        label="沉穩步伐",
        description="以恆定的節奏強化身體的基礎能力。",
        kind=SkillKind.PASSIVE,
        target_spec=TargetSpec.SELF,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[
            f"stat_multiply:{trait}:1.1"
            for trait in ("atk_phys", "agility", "defense")
        ],
        category=SkillCategory.ENHANCEMENT,
    ),
    "t_moss_veil": SkillDef(
        key="t_moss_veil",
        label="苔幕",
        description="召出覆蓋苔屑的防護霧幕。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SELF,
        cost={"mp": 13},
        usable_out_of_combat=True,
        element=None,
        effects=["self_buff_apply:t_moss_veil"],
        category=SkillCategory.ENHANCEMENT,
    ),
    # Element-anchored pair for the freeform scale ladder
    # (use-driven-skill-lineage DC5 / element-mastery-freeform-casting): the
    # entitlement key is f"{element.key}_mastery", so the mastery passive is
    # keyed off the kit's OWN invented element and the paired active spell
    # scales with it. Fully t_-keyed: no shipped mastery row is borrowed (the
    # borrowed seam is the closed element VOCABULARY, not the skill keys).
    "t_glowmire_mastery": SkillDef(
        key="t_glowmire_mastery",
        label="光沼精通",
        description="被動提昇光沼系魔法的掌握程度與威力。",
        kind=SkillKind.PASSIVE,
        target_spec=TargetSpec.NONE,
        cost={},
        usable_out_of_combat=True,
        element=SYNTH_GLOWMIRE_ELEMENT,
        # No shipped passive-trait effect string: the freeform entitlement
        # reads DIRECT OWNERSHIP of the f"{element}_mastery" key, never an
        # effect layer, and the shipped effect name would collide with the
        # shipped token universe the kit must stay clear of.
        effects=[],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=SYNTH_GLOWMIRE_ELEMENT.key,
    ),
    "t_glowmire_bloom": SkillDef(
        key="t_glowmire_bloom",
        label="光沼花綻",
        description="讓光沼的魔力在戰場上綻放成覆蓋的魔法波濤。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.AREA,
        cost={"mp": 14},
        usable_out_of_combat=True,
        element=SYNTH_GLOWMIRE_ELEMENT,
        effects=["damage:t_glowmire:magic"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=SYNTH_GLOWMIRE_ELEMENT.key,
    ),
    # Zero-cost NONE utility: the NONE-shape cast carrier (the shipped
    # concentrate analogue) for the combat-menu acceptance journeys.
    "t_cinder_breath": SkillDef(
        key="t_cinder_breath",
        label="燼息",
        description="吐出一口溫熱的燼息，安撫自身的傷勢。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.NONE,
        cost={"mp": 5},
        usable_out_of_combat=True,
        element=None,
        effects=["self_buff_apply:t_moss_veil"],
        category=SkillCategory.UTILITY,
    ),
    # Utility row the combat menu must expose disabled with an explanation
    # (combat-menu H3 seam). The race gate is the live mechanism: every
    # shipped effect handler became context-free (divine-veil-cast-path made
    # ``set_disguise`` context-free, conferral-grant-store made
    # ``confer_skill_partial`` read its scale from node data), so the row
    # rides the divine-arts race gate instead — the kit's only race has no
    # divine affinity, mirroring the shipped fixture's human casting a divine
    # row (the carrier keeps its place as the panel's first-owned utility
    # row).
    "t_rock_quietus": SkillDef(
        key="t_rock_quietus",
        label="岩中授語",
        description="以岩層深處的寂靜，將沉穩的步伐授與目標。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        requires_divine_arts=True,
        effects=["confer_skill_partial"],
        category=SkillCategory.UTILITY,
    ),
}

# One synthetic sexual act: the paired SkillDef shares the act key and lives
# in the same (patched) skill registry as shipped rows.
SYNTH_ACT_SKILL = SkillDef(
    key="t_hush_brush",
    label="噤聲輕撫",
    description="以極輕的觸撫試探對方靜止的呼吸。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[
        "pleasure:t_hush_brush",
        "sexual_counter:t_hush_brush",
        "sexual_event:self_exposure",
    ],
    category=SkillCategory.SEXUAL_ACT,
    group="t_合成",
)
SYNTH_ACT = SexualActDef(
    key="t_hush_brush",
    unlock={},
    base_pleasure=6,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.5,
    actor_counters=(),
    participant_counters=(),
    sexual_events=("self_exposure",),
    resistible=False,
)
SYNTH_SKILLS[SYNTH_ACT.key] = SYNTH_ACT_SKILL
SYNTH_ACTS: dict[str, SexualActDef] = {SYNTH_ACT.key: SYNTH_ACT}

SYNTH_MP_COST_TIERS: dict[str, CostTier] = {
    "t_ash_adept": CostTier(0, 15, (10, 16), (14, 20)),
    "t_cinder_sage": CostTier(16, 90, (20, 60), (26, 90)),
}
