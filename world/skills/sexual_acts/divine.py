"""神之秘法線 (divine arts line): acts that deliberately break the balance
the other five lines rely on.

Filled by the divine-sexual-arts proposals; this change ships the module
pre-declared and empty so that those proposals own exactly this one file.
"""

from world.skills.registry import SkillDef
from world.skills.sexual_acts._builder import SexualActDef

DIVINE_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
