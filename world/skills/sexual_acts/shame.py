"""羞恥線 (shame line): exposure- and shame-driven acts.

Filled by the sexual-catalog-shame proposal; this change ships the module
pre-declared and empty so that proposal owns exactly this one file.
"""

from world.skills.registry import SkillDef
from world.skills.sexual_acts._builder import SexualActDef

SHAME_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
