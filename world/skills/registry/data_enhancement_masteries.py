"""Registry data slice: the three body-enhancement multiplier tiers and the eight element-mastery passives.

Moved verbatim from the ``SKILL_REGISTRY`` literal in
``world/skills/registry.py``; ``ROWS`` is the contiguous, in-order
entry block (section comments included) the assembly concatenates.
Do not reorder or edit rows here: registry order is observable.

Each element mastery declares every ordinary terminal of its unrestricted
elemental ACTIVE catalog at the proficiency tip cap
(use-driven-progression §9.1 amended): ``fire_mastery`` and its seven
siblings are the whole-tree reward, so a mastery is lawful only when the
entire closure below it is directly owned and practised. The declared
terminals are the ordinary catalog's own leaf nodes — identity-restricted
monster rows, element-tagged martial skills and independent enhancement
passives stay outside the universe — and adding a tip-cap consumer leaves
each terminal's derived cap unchanged.
"""

from world.skills.registry.builders import (
    _body_multiplier,
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
        _body_multiplier("body_enhancement", "身體強化", 100),
        _body_multiplier("body_enhancement_extreme", "身體超強化", 1000),
        _body_multiplier("body_enhancement_basic", "基礎身體強化", 1.2),
        _skill(
            "fire_mastery",
            "火焰精通",
            "習得火屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整火屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="fire",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="fire",
            prerequisites=(
                SkillPrerequisite("flame_shroud", 10),
                SkillPrerequisite("scorching_armor", 10),
                SkillPrerequisite("crimson_apotheosis", 10),
            ),
        ),
        _skill(
            "dark_mastery",
            "闇影精通",
            "習得闇屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整闇屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="dark",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="dark",
            prerequisites=(
                SkillPrerequisite("dark_dominion", 10),
                SkillPrerequisite("abyssal_apotheosis", 10),
            ),
        ),
        _skill(
            "wind_mastery",
            "疾風精通",
            "習得風屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整風屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="wind",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="wind",
            prerequisites=(
                SkillPrerequisite("haste_domain", 10),
                SkillPrerequisite("sky_apotheosis", 10),
            ),
        ),
        _skill(
            "light_mastery",
            "光輝精通",
            "習得光屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整光屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="light",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="light",
            prerequisites=(
                SkillPrerequisite("sanctified_ward", 10),
                SkillPrerequisite("goddess_blessing", 10),
                SkillPrerequisite("bliss_apotheosis", 10),
            ),
        ),
        _skill(
            "water_mastery",
            "水流精通",
            "習得水屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整水屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="water",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="water",
            prerequisites=(
                SkillPrerequisite("water_shield", 10),
                SkillPrerequisite("abyssal_surge", 10),
                SkillPrerequisite("abyssal_maw", 10),
                SkillPrerequisite("abyssal_heart", 10),
            ),
        ),
        _skill(
            "earth_mastery",
            "大地精通",
            "習得土屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整土屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="earth",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="earth",
            prerequisites=(
                SkillPrerequisite("earthen_ward", 10),
                SkillPrerequisite("thorned_carapace", 10),
                SkillPrerequisite("earthen_apotheosis", 10),
            ),
        ),
        _skill(
            "lightning_mastery",
            "雷霆精通",
            "習得雷屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整雷屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="lightning",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="lightning",
            prerequisites=(
                SkillPrerequisite("thunder_shatter_strike", 10),
                SkillPrerequisite("thunder_prison", 10),
                SkillPrerequisite("thunder_apotheosis", 10),
            ),
        ),
        _skill(
            "ice_mastery",
            "寒冰精通",
            "習得冰屬性系譜的所有分支後方能領會的元素精通；持有者得以自由調整冰屬性法術的威力與消耗。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="ice",
            effects=["passive_trait:element_mastery"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            group="ice",
            prerequisites=(
                SkillPrerequisite("frost_mire", 10),
                SkillPrerequisite("crystal_shatter", 10),
                SkillPrerequisite("eternal_frost_apotheosis", 10),
            ),
        ),
)
