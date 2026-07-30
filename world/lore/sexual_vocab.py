"""Ordered sexual-state vocabularies shared by imports and future rules.

``CHARACTER_SCHEMA_V1`` is the current consumer.  The later sexual-state
change must import these tuples rather than redefining their ordering.
"""

AROUSAL_LEVELS = ("平靜", "微興奮", "中等", "高度", "極限")
WETNESS_LEVELS = ("乾燥", "微濕", "濕潤", "大量", "泛濫")
SHAME_LEVELS = ("無", "輕微", "中等", "強烈", "成癮")
EXPOSURE_LEVELS = ("極低", "低", "中等", "高", "極高")
CLIMAX_PHASE_LEVELS = ("未達", "接近", "進行中", "餘韻")
SENSITIVITY_LEVELS = ("普通", "高", "極高", "敏感異常")

__all__ = [
    "AROUSAL_LEVELS",
    "CLIMAX_PHASE_LEVELS",
    "EXPOSURE_LEVELS",
    "SENSITIVITY_LEVELS",
    "SHAME_LEVELS",
    "WETNESS_LEVELS",
]
