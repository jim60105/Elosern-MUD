"""Sexual-state vocabularies shared by imports and future rules.

This module is the single source for these level-name vocabularies.
``import-contract``, the change that introduced them, is their first
consumer; ``CHARACTER_SCHEMA_V1`` is the current consumer of the six
ordered-level tuples.  The later sexual-state change, which introduces
the ordered-level ``Trait`` subclass (design doc §6.4), must import
these tuples rather than redefining their ordering.

``BODY_PARTS`` and ``GENERIC_BODY_PART`` have no current consumer; they
ship ahead of the future sexual-act-registry and sexual-act-effects
capabilities, which are expected to import these constants rather than
redefine the vocabulary or invent a per-monster-archetype body-part table.
"""

AROUSAL_LEVELS = ("平靜", "微興奮", "中等", "高度", "極限")
WETNESS_LEVELS = ("乾燥", "微濕", "濕潤", "大量", "泛濫")
SHAME_LEVELS = ("無", "輕微", "中等", "強烈", "成癮")
EXPOSURE_LEVELS = ("極低", "低", "中等", "高", "極高")
CLIMAX_PHASE_LEVELS = ("未達", "接近", "進行中", "餘韻")
SENSITIVITY_LEVELS = ("普通", "高", "極高", "敏感異常")

BODY_PARTS = ("口唇", "頸項", "耳朵", "乳房", "腰腹", "臀部", "大腿", "足部", "私處", "後庭")
GENERIC_BODY_PART = "軀體"

assert GENERIC_BODY_PART not in BODY_PARTS

__all__ = [
    "AROUSAL_LEVELS",
    "BODY_PARTS",
    "CLIMAX_PHASE_LEVELS",
    "EXPOSURE_LEVELS",
    "GENERIC_BODY_PART",
    "SENSITIVITY_LEVELS",
    "SHAME_LEVELS",
    "WETNESS_LEVELS",
]