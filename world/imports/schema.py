"""Frozen version-one JSON Schemas for imported records."""

import re

from world.art.subjects import (
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_LENGTH,
)
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)

_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_NONNEGATIVE = {"type": "integer", "minimum": 0}

# The shared entity-key contract (fix-art-pipeline-contracts D1):
# ``world/art/subjects.py`` hosts the single constant set (reserved
# separators and the 64-character bound); the schema derives its structural
# pattern from it, so the import pipeline and every art producer enforce
# exactly the same rule set. The pattern uses absolute ``\\A``/``\\Z``
# anchors so a trailing newline or any other excluded character fails the
# whole-string match (the naive ``^...$`` form would let ``$`` match before
# a final newline).
MAX_ENTITY_KEY_LENGTH = MAX_SUBJECT_KEY_LENGTH
_FORBIDDEN_CLASS = "".join(
    re.escape(char) for char in sorted(FORBIDDEN_SUBJECT_KEY_CHARACTERS)
)
ENTITY_KEY_PATTERN_V1 = (
    rf"\A[^{_FORBIDDEN_CLASS}\x00-\x1f\x7f\x80-\x9f]{{1,{MAX_ENTITY_KEY_LENGTH}}}\Z"
)
_ENTITY_KEY_RULES = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_ENTITY_KEY_LENGTH,
    "pattern": ENTITY_KEY_PATTERN_V1,
}

CHARACTER_SCHEMA_V1 = {
    "$schema": _DRAFT,
    "title": "CHARACTER_SCHEMA_V1",
    "type": "object",
    "required": [
        "record_type",
        "schema_version",
        "key",
        "display_name",
        "age",
        "apparent_age",
        "race",
        "subrace",
        "stats",
        "disguised_stats",
        "skills",
        "passives",
        "equipment",
        "inventory",
        "sexual_baseline",
        "persona",
    ],
    "properties": {
        "record_type": {
            "const": "character",
            "description": (
                "Required discriminator used by validate.py so incomplete records "
                "cannot be silently routed to WORLD_SCHEMA_V1 by field guessing."
            ),
        },
        "schema_version": {"const": 1},
        "key": dict(_ENTITY_KEY_RULES),
        "display_name": {"type": "string", "minLength": 1},
        "age": {
            "type": "integer",
            "minimum": 18,
            "description": (
                "HARD GATE: every imported character must be an adult. This is a "
                "code-level invariant and always rejects; it is never a warning."
            ),
        },
        "apparent_age": {
            "type": "integer",
            "minimum": 18,
            "description": (
                "Independent HARD GATE: characters who appear underage always "
                "reject even when age is adult; this is never a warning."
            ),
        },
        "race": {"type": "string", "minLength": 1},
        "subrace": {"type": "string", "minLength": 1},
        "stats": {
            "type": "object",
            "description": (
                "BASE values only, before skill multipliers. Source notation "
                "88*1000 means store 88 here and apply the x1000 skill multiplier "
                "during resolution; it never means a stored value of 88000."
            ),
            "properties": {
                "hp": {"type": "integer", "minimum": 1},
                "mp": dict(_NONNEGATIVE),
                "sp": dict(_NONNEGATIVE),
                "atk_phys": dict(_NONNEGATIVE),
                "agility": dict(_NONNEGATIVE),
                "defense": dict(_NONNEGATIVE),
                "magic_level": dict(_NONNEGATIVE),
                "guild_merit": dict(_NONNEGATIVE),
            },
            "additionalProperties": False,
        },
        "disguised_stats": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        },
        "skills": {"type": "array", "items": {"type": "string"}},
        "passives": {"type": "array", "items": {"type": "string"}},
        "equipment": {"type": "object"},
        "inventory": {"type": "array"},
        "sexual_baseline": {
            "type": "object",
            "required": ["arousal", "virgin", "sensitivity"],
            "properties": {
                "arousal": {"enum": list(AROUSAL_LEVELS)},
                "wetness": {"enum": list(WETNESS_LEVELS)},
                "shame": {"enum": list(SHAME_LEVELS)},
                "exposure": {"enum": list(EXPOSURE_LEVELS)},
                "climax_phase": {"enum": list(CLIMAX_PHASE_LEVELS)},
                "sensitivity": {
                    "type": "object",
                    "additionalProperties": {"enum": list(SENSITIVITY_LEVELS)},
                },
                "virgin": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "persona": {
            "type": "object",
            "description": (
                "Opaque persona payload. Validation confirms only that it is an "
                "object and never inspects or constrains its nested content."
            ),
        },
        "affinity_elements": {
            "type": "array",
            "items": {
                "enum": [
                    "fire", "water", "wind", "earth",
                    "lightning", "ice", "light", "dark",
                ],
            },
            "uniqueItems": True,
            "maxItems": 8,
            "description": (
                "Optional element-affinity set for cast-tier progression. At most "
                "8 unique lowercase keys from exactly the eight lore elements. An "
                "absent or empty array means neutral progression; an elf record "
                "must not supply a set (its affinity is subrace-derived, enforced "
                "semantically)."
            ),
        },
    },
    "additionalProperties": False,
}

WORLD_SCHEMA_V1 = {
    "$schema": _DRAFT,
    "title": "WORLD_SCHEMA_V1",
    "type": "object",
    "required": ["record_type", "schema_version", "key", "content"],
    "properties": {
        "record_type": {
            "const": "world_entry",
            "description": "Required discriminator selecting WORLD_SCHEMA_V1.",
        },
        "schema_version": {"const": 1},
        "key": dict(_ENTITY_KEY_RULES),
        "display_name": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "content": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Opaque narrative flavor for generative prompts only; never a "
                "source of mechanical truth, which remains in world/lore/."
            ),
        },
    },
    "additionalProperties": False,
}
