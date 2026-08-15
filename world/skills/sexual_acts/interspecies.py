"""異種線 (interspecies line): acts performed against monsters.

Filled by the sexual-catalog-interspecies proposal; this change ships the
module pre-declared and empty so that proposal owns exactly this one file.
"""

from world.skills.registry import SkillDef
from world.skills.sexual_acts._builder import SexualActDef

INTERSPECIES_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
