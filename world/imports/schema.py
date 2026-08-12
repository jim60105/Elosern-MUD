"""Frozen version-one JSON Schemas for imported records."""

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

# The shared entity-key contract (fix-import-key-validity D1): printable
# characters excluding the structural separators ``|``, ``/``, ``:``, ``{``,
# ``}`` and control characters (C0, DEL, C1), bounded at 64 characters. The
# pattern uses absolute ``\\A``/``\\Z`` anchors so a trailing newline or any
# other excluded character fails the whole-string match. This rule set is
# mirrored by the art stable-key change (``fix-art-pipeline-contracts``) so no
# producer set drifts; both changes use identical constants.
MAX_ENTITY_KEY_LENGTH = 64
ENTITY_KEY_PATTERN_V1 = r"\A[^|/:{}\x00-\x1f\x7f\x80-\x9f]{1,64}\Z"
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
