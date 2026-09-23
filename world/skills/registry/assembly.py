"""``SKILL_REGISTRY`` assembly: the domain data slices in global order.

The registry is constructed from the verbatim domain slices in exactly the
order the single ``SKILL_REGISTRY`` literal in ``world/skills/registry.py``
listed them (basic_attack first, the crown capstone last). Dict iteration
order is observable (tier derivation, lineage ordering, data-lint), so the
concatenation order below is frozen.
"""

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

SKILL_REGISTRY: dict[str, SkillDef] = {
    skill.key: skill
    for skill in (
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
    )
}
