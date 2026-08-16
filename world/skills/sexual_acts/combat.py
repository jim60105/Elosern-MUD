"""戰鬥線 (combat line): hostile acts performed during combat.

Ships the one seed act this change registers; the sexual-catalog-combat
proposal appends the remaining acts to this same tuple and owns no other
file. This module is distinct from ``world/rules/combat.py``; the two are
unambiguous by full path.
"""

from world.skills.registry import SkillDef, TargetSpec
from world.skills.sexual_acts._builder import SexualActDef, _act_family

COMBAT_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = _act_family(
    "戰鬥",
    (
        "combat_tease",
        "挑逗",
        "在交鋒之間以言語與動作挑逗對方，擾亂對手的節奏。",
        TargetSpec.SINGLE,
        {},
        7,
        "腰腹",
        "腰腹",
        0.4,
        ("hostile_act_count",),
        (),
        (),
        True,
    ),
)
