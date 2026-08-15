"""戰鬥線 (combat line): hostile acts performed during combat.

Filled by the sexual-catalog-combat proposal; this change ships the module
pre-declared and empty so that proposal owns exactly this one file. This
module is distinct from ``world/rules/combat.py``; the two are unambiguous
by full path.
"""

from world.skills.registry import SkillDef
from world.skills.sexual_acts._builder import SexualActDef

COMBAT_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
