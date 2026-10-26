"""Frozen version-one JSON Schemas for imported records."""

import re

from world.art.subjects import (
    DIGITS_ONLY_KEY_PATTERN,
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_LENGTH,
)
from world.lore.sex import SEX_VALUES
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.npc_identity import MAX_NPC_TITLE_CODE_POINTS

_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_NONNEGATIVE = {"type": "integer", "minimum": 0}

# The shared entity-key contract (fix-art-pipeline-contracts D1):
# ``world/art/subjects.py`` hosts the single constant set (reserved
# separators and the 64-character bound); the schema derives its structural
# pattern from it, so the import pipeline and every art producer enforce
# exactly the same rule set. The pattern uses absolute ``\\A``/``\\Z``
# anchors so a trailing newline or any other excluded character fails the
# whole-string match (the naive ``^...$`` form would let ``$`` match before
# a final newline). The digit-only negative lookahead is derived from the
# shared ``DIGITS_ONLY_KEY_PATTERN``: the digit-only region of the
# character-portrait keyspace is reserved for player pks (``str(pk)``), so an
# imported entity key can never collide with a player's portrait subject
# (fix-portrait-stable-key-collision D1/D2).
MAX_ENTITY_KEY_LENGTH = MAX_SUBJECT_KEY_LENGTH
_FORBIDDEN_CLASS = "".join(
    re.escape(char) for char in sorted(FORBIDDEN_SUBJECT_KEY_CHARACTERS)
)
ENTITY_KEY_PATTERN_V1 = (
    rf"\A(?!{DIGITS_ONLY_KEY_PATTERN}\Z)"
    rf"[^{_FORBIDDEN_CLASS}\x00-\x1f\x7f\x80-\x9f]{{1,{MAX_ENTITY_KEY_LENGTH}}}\Z"
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
        "title",
        "age",
        "apparent_age",
        "race",
        "subrace",
        "sex",
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
        # The rule set is deliberately NOT duplicated here as a pattern or a
        # maxLength keyword: the bound applies to the validator's STRIPPED
        # form, and a raw maxLength would reject values the validator
        # canonicalizes and accepts (splitting the single-validator contract
        # that npc-identity-titles declares). Length and character rules are
        # enforced solely by ``validate_npc_title`` in the semantic phase.
        "title": {
            "type": "string",
            "minLength": 1,
            "description": (
                "REQUIRED single-line plain-text NPC title (南門守衛, 雜貨店老闆). "
                "The full rule set -- 1 to "
                f"{MAX_NPC_TITLE_CODE_POINTS} code points after stripping, no "
                "whitespace (including the full-width space U+3000), no control "
                "characters, no '|' -- is enforced semantically by "
                "world.rules.npc_identity.validate_npc_title, the single "
                "validator every NPC-title write path shares. The field takes "
                "effect only for NPC imports."
            ),
        },
        "age": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000,
            "description": (
                "Canonical age in years; reasonable range 0-10000. Values "
                "outside the range always reject."
            ),
        },
        "apparent_age": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000,
            "description": (
                "Apparent age in years; reasonable range 0-10000. Validated "
                "independently of age: values outside the range always reject."
            ),
        },
        "race": {"type": "string", "minLength": 1},
        "subrace": {"type": "string", "minLength": 1},
        "sex": {"enum": list(SEX_VALUES)},
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
                "magic_power": dict(_NONNEGATIVE),
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
        "skill_proficiency": {
            "type": "object",
            "propertyNames": {"type": "string"},
            "additionalProperties": {"type": "number", "minimum": 0},
            "description": (
                "Optional explicit practice XP per skill key; auto-seed fills "
                "unsatisfied prerequisite edges with the exact required value, "
                "and an explicit entry always wins."
            ),
        },
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
                "Persona payload. The schema checks only that it is an object. "
                "An NPC-target import applies the compact NPC card contract "
                "during semantic validation (world.lore.npc_card); a non-NPC "
                "target's persona is opaque and never inspected."
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
        "combat_traits": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["undead"],
            },
            "uniqueItems": True,
            "description": (
                "Optional combat-trait classifications for conditional effects. "
                "Initially accepts only 'undead'. Absent or empty array means "
                "neutral classification."
            ),
        },
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "kwargs"],
                "properties": {
                    "type": {"type": "string", "minLength": 1},
                    "kwargs": {
                        "type": "object",
                        "propertyNames": {"type": "string"},
                    },
                    "binding": {
                        "description": (
                            "Optional availability binding of one capability. "
                            "{kind: 'person'} makes the service travel with its "
                            "host (co-presence); {kind: 'place', anchor_room: "
                            "<room tag>} anchors it to exactly one room, resolved "
                            "by tag inside the import transaction. Required for "
                            "every service capability (merchant, guild_staff, "
                            "guild_exam_reception, quest_issuer, church_host) and "
                            "omitted by ordinary narrative dialogue. An anchor on "
                            "a person binding is the invalid combination."
                        ),
                        "anyOf": [
                            {
                                "type": "object",
                                "required": ["kind"],
                                "additionalProperties": False,
                                "properties": {"kind": {"const": "person"}},
                            },
                            {
                                "type": "object",
                                "required": ["kind", "anchor_room"],
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {"const": "place"},
                                    "anchor_room": {"type": "string", "minLength": 1},
                                },
                            },
                        ],
                    },
                },
                "additionalProperties": False,
            },
            "description": (
                "Optional direct NPC capability declarations "
                "[{type, kwargs, binding?}]. Each entry names one capability of "
                "the closed vocabulary and authors exactly that capability's "
                "configuration (service_id, shop_key, branch_key, dialogue_key, "
                "issuer_key, church, initial_arousal as its type defines); the "
                "loader never invents or defaults an identifier. Entries are "
                "independent: no blueprint expands, no ordering decides "
                "anything, and one entry per type is allowed. Declarations are "
                "validated as a complete batch before anything is constructed, "
                "and only for NPC-targeted imports."
            ),
        },
        "social_identities": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
            "maxItems": 8,
            "uniqueItems": True,
            "description": (
                "Optional array of up to 8 unique registered social identity "
                "tags (noble, clergy, official, adventurer). Unknown keys, "
                "duplicates, and non-string values fail validation."
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
