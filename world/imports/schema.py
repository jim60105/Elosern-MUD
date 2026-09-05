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
        "profession": {
            "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}],
            "description": (
                "Optional assembly-time profession blueprint key. A non-null value "
                "must name a row of the loaded profession rulebook "
                "(world/rules/profession_config.py); an unknown key rejects the "
                "record in the shared batch validator. null or an absent field "
                "means no profession. The blueprint assembles NPC components, "
                "applies the row's schedule template, and supplies a default tier; "
                "it takes effect only for NPC-targeted imports and never overrides "
                "the record's own literal stats."
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
                },
                "additionalProperties": False,
            },
            "description": (
                "Optional explicit per-record component assembly entries "
                "[{type, kwargs}]. An entry's type must name a key of the "
                "profession component vocabulary and its kwargs are the authored "
                "service-identity values (service_id, shop_key, branch_key, "
                "dialogue_key as the component class defines them); the loader "
                "never invents identity. Entries override the profession "
                "blueprint for their type (design D5) and may add vocabulary "
                "components the blueprint omits. Valid only alongside a "
                "profession; only for NPC-targeted imports."
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
