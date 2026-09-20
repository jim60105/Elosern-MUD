"""Loaded balance constants for the progression rules package.

Owns ``PROGRESSION_YAML`` and every scalar derived from it at import time
(the original single-module load order, first definition site).
"""

from math import isfinite
from pathlib import Path
from typing import Any

import yaml

PROGRESSION_YAML = yaml.safe_load(
    (Path(__file__).parents[1] / "rulebook" / "progression.yaml").read_text(
        encoding="utf-8"
    )
)
SKILL_PROFICIENCY_XP_PER_LEVEL = float(
    PROGRESSION_YAML["skill_proficiency_xp_per_level"]
)
SKILL_PRACTICE_XP_PER_USE = float(PROGRESSION_YAML["skill_practice_xp_per_use"])
AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["affinity_element_multiplier"]
)
NON_AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["non_affinity_element_multiplier"]
)
PRACTICE_XP_PER_STUDY_HOUR = float(PROGRESSION_YAML["practice_xp_per_study_hour"])
if not isfinite(PRACTICE_XP_PER_STUDY_HOUR) or PRACTICE_XP_PER_STUDY_HOUR <= 0:
    raise ValueError("practice_xp_per_study_hour must be a positive finite number")


FREEFORM_CAST_SCALE_COUNT = 5

# D6 canopy default: the tip cap of a skill nobody consumes in the
# prerequisite graph.
PROFICIENCY_TIP_CAP = int(PROGRESSION_YAML["proficiency_tip_cap"])
if PROFICIENCY_TIP_CAP < 1:
    raise ValueError("proficiency_tip_cap must be >= 1")
