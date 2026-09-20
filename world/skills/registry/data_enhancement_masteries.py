"""Registry data slice: the three body-enhancement multiplier tiers and the eight element-mastery passives.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.
"""

from world.skills.registry.builders import (
    _body_multiplier,
    _skill,
)

from world.skills.registry.vocab import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
        _body_multiplier("body_enhancement", "身體強化", 100),
        _body_multiplier("body_enhancement_extreme", "身體超強化", 1000),
        _body_multiplier("body_enhancement_basic", "基礎身體強化", 1.2),
        _skill(
            "fire_mastery",
            "火焰精通",
            "被動提昇火焰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="fire",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
        ),
        _skill(
            "dark_mastery",
            "闇屬性精通",
            "被動提昇闇屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="dark",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
        ),
        _skill(
            "wind_mastery",
            "風屬性精通",
            "被動提昇風屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="wind",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
        ),
        _skill(
            "light_mastery",
            "光屬性精通",
            "被動提昇光屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="light",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
        ),
        _skill(
            "water_mastery",
            "水屬性精通",
            "被動提昇水系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="water",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
        ),
        _skill(
            "earth_mastery",
            "土屬性精通",
            "被動提昇土系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="earth",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
        ),
        _skill(
            "lightning_mastery",
            "雷屬性精通",
            "被動提昇雷系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="lightning",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
        ),
        _skill(
            "ice_mastery",
            "冰屬性精通",
            "被動提昇冰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="ice",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
        ),
)
