"""``SKILL_REGISTRY`` assembly: the domain data slices in global order.

The registry is constructed from the verbatim domain slices in exactly the
order the single ``SKILL_REGISTRY`` literal in ``world/skills/registry.py``
listed them (basic_attack first, the crown capstone last). Dict iteration
order is observable (tier derivation, lineage ordering, data-lint), so the
concatenation order below is frozen.
"""

from collections.abc import Mapping
from types import MappingProxyType

from world.skills.registry.vocab import SkillDef
from world.skills.registry.data_martial_sword import ROWS as MARTIAL_SWORD_ROWS
from world.skills.registry.data_enhancement_masteries import ROWS as ENHANCEMENT_MASTERIES_ROWS
from world.skills.registry.data_fire import ROWS as FIRE_ROWS
from world.skills.registry.data_water import ROWS as WATER_ROWS
from world.skills.registry.data_earth import ROWS as EARTH_ROWS
from world.skills.registry.data_wind import ROWS as WIND_ROWS
from world.skills.registry.data_lightning import ROWS as LIGHTNING_ROWS
from world.skills.registry.data_ice import ROWS as ICE_ROWS
from world.skills.registry.data_light import ROWS as LIGHT_ROWS
from world.skills.registry.data_dark import ROWS as DARK_ROWS
from world.skills.registry.data_shadow_martial import ROWS as SHADOW_MARTIAL_ROWS
from world.skills.registry.data_utility_passives import ROWS as UTILITY_PASSIVES_ROWS
from world.skills.registry.data_divine_mystery import ROWS as DIVINE_MYSTERY_ROWS
from world.skills.registry.data_church import ROWS as CHURCH_ROWS
from world.skills.registry.data_monster_abilities import ROWS as MONSTER_ABILITIES_ROWS

#: The shipped rows, the domain slices concatenated in frozen global order.
_ROWS: tuple[SkillDef, ...] = (
    *MARTIAL_SWORD_ROWS,
    *ENHANCEMENT_MASTERIES_ROWS,
    *FIRE_ROWS,
    *WATER_ROWS,
    *EARTH_ROWS,
    *WIND_ROWS,
    *LIGHTNING_ROWS,
    *ICE_ROWS,
    *LIGHT_ROWS,
    *DARK_ROWS,
    *SHADOW_MARTIAL_ROWS,
    *UTILITY_PASSIVES_ROWS,
    *DIVINE_MYSTERY_ROWS,
    *CHURCH_ROWS,
    *MONSTER_ABILITIES_ROWS,
)

SKILL_REGISTRY: dict[str, SkillDef] = {skill.key: skill for skill in _ROWS}

#: The shipped catalog as an immutable snapshot, taken here — before any
#: consumer exists that could substitute the live ``SKILL_REGISTRY`` binding.
#: The synthetic test-data kit replaces that binding for the duration of a
#: scope by mutating the live dict in place (``patch.dict``: every consumer
#: binding *is* the same dict object), so inside a scope the live binding holds
#: kit rows only and carries no shipped row at all. A module that loads and
#: validates a SHIPPED rulebook at import (``world.rules.cross_lineage_unlock``,
#: ``world.rules.guild_exam_restrictions``) therefore reads this snapshot: its
#: load must not depend on whether something already imported it outside a
#: synthetic catalog scope. Runtime ownership checks keep reading the live
#: binding — they must see whatever catalog the running scope installed.
SHIPPED_SKILL_REGISTRY: Mapping[str, SkillDef] = MappingProxyType(
    dict(SKILL_REGISTRY)
)
