"""Canonical bounded scene-package proposal schema (quest-scene-encounters 4.4).

The ScenarioDirector may propose a whole scene package as plain bounded data:
reusable named roles, typed relationships, role-owned knowledge, independently
eligible encounters, complete per-role dialogue phases, an embedded quest
blueprint, and an optional symbolic role-issued commission. This module owns the
*structural* contract (exact keys, closed vocabularies, and the size bounds the
resolver and panel already respect); the deterministic quest boundary owns the
semantic contract (registry references, ownership, phase coverage, authority).
Both derive from the same payload shape, so a proposal can never reach storage
unvalidated.

This module reads nothing and writes nothing: it is pure schema data plus a pure
structural check, and it imports no state writer, typeclass, or transport.
"""

from __future__ import annotations

from typing import Any

#: The closed structural vocabularies the payload may name. Registry keys
#: (tier, archetype, anchor, item, quest type, rank) are validated semantically
#: against the immutable lore registries by the deterministic boundary.
DESTINATION_LAYERS: tuple[str, ...] = ("anchor", "grid", "instance")
OBJECTIVE_KINDS: tuple[str, ...] = (
    "reach_location",
    "defeat",
    "acquire",
)
RELATIONSHIP_KINDS: tuple[str, ...] = ("parent_child",)
EFFECT_VERBS: tuple[str, ...] = ("offer_commission",)
#: The closed escort completion discriminator. Duplicated here rather than
#: imported because ``world/ai`` may not import the ``world.quests`` state
#: writer package; a repository-wide drift test pins it equal to
#: ``world.quests.definitions.EscortCompletion``.
ESCORT_COMPLETIONS: tuple[str, ...] = ("destination", "rendezvous")

MAX_ID_LENGTH = 64
MAX_PROSE = 500
MAX_TOPICS = 8
MAX_ROLES = 32
MAX_ENCOUNTERS = 16
MAX_PHASES = 16
MAX_CLAIMS = 64

_LOCATOR = {
    "type": "object",
    "required": ["layer"],
    "additionalProperties": False,
    "properties": {
        "layer": {"enum": list(DESTINATION_LAYERS)},
        "anchor_key": {"type": ["string", "null"], "maxLength": MAX_ID_LENGTH},
        "xyz": {
            "type": ["array", "null"],
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": ["integer", "string"]},
        },
        "archetype": {"type": ["string", "null"], "maxLength": MAX_ID_LENGTH},
        "anchor_near": {"type": ["string", "null"], "maxLength": MAX_ID_LENGTH},
        "scene_sentence": {"type": ["string", "null"], "maxLength": MAX_PROSE},
    },
}

_CONDITION = {
    "type": "object",
    "minProperties": 1,
    "maxProperties": 1,
    "additionalProperties": {"type": ["boolean", "string"], "maxLength": MAX_ID_LENGTH},
}

_ROLE = {
    "type": "object",
    "required": ["role_id", "tier", "characterization", "conversable", "retention"],
    "additionalProperties": False,
    "properties": {
        "role_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
        "tier": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
        "disposition": {"type": ["string", "null"], "maxLength": MAX_ID_LENGTH},
        "conversable": {"type": "boolean"},
        "retention": _LOCATOR,
        "existing_npc": {
            "type": "object",
            "required": ["kind", "value"],
            "additionalProperties": False,
            "properties": {
                "kind": {"enum": ["pk"]},
                "value": {"type": "integer", "minimum": 1},
            },
        },
        "characterization": {
            "type": "object",
            "required": ["display_name", "title", "persona"],
            "additionalProperties": False,
            "properties": {
                "display_name": {"type": "string", "minLength": 1, "maxLength": 64},
                "title": {"type": "string", "minLength": 1, "maxLength": 64},
                "age": {"type": ["integer", "null"], "minimum": 0, "maximum": 10000},
                "apparent_age": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "maximum": 10000,
                },
                "portrait": {
                    "type": ["object", "null"],
                    "required": ["stable_key"],
                    "additionalProperties": False,
                    "properties": {
                        "stable_key": {"type": "string", "minLength": 1, "maxLength": 64}
                    },
                },
                "persona": {"type": "object"},
                "combat_traits": {
                    "type": ["array", "null"],
                    "items": {"type": "string", "maxLength": MAX_ID_LENGTH},
                },
            },
        },
    },
}

_TOPIC = {
    "type": "object",
    "required": ["keyword", "response"],
    "additionalProperties": False,
    "properties": {
        "keyword": {"type": "string", "minLength": 1, "maxLength": 32},
        "response": {"type": "string", "minLength": 1, "maxLength": MAX_PROSE},
        "effect_verb": {"enum": list(EFFECT_VERBS)},
        "effect_reference": {"type": "string", "minLength": 1, "maxLength": 128},
    },
}

_PHASE = {
    "type": "object",
    "required": [
        "phase_id",
        "conditions",
        "greeting",
        "topics",
        "freeform_situation",
        "freeform_goals",
        "offline_response",
    ],
    "additionalProperties": False,
    "properties": {
        "phase_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
        "conditions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 4,
            "items": _CONDITION,
        },
        "greeting": {"type": "string", "minLength": 1, "maxLength": MAX_PROSE},
        "topics": {"type": "array", "maxItems": MAX_TOPICS, "items": _TOPIC},
        "freeform_situation": {"type": "string", "maxLength": MAX_PROSE},
        "freeform_goals": {"type": "string", "maxLength": MAX_PROSE},
        "offline_response": {"type": "string", "minLength": 1, "maxLength": MAX_PROSE},
    },
}

_ESCORT_RESULT = {
    "type": "object",
    "required": ["completion", "protected_role_refs"],
    "additionalProperties": False,
    "properties": {
        "completion": {"enum": list(ESCORT_COMPLETIONS)},
        "protected_role_refs": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ROLES,
            "items": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
        },
        "meeting_role_refs": {
            "type": "array",
            "maxItems": MAX_ROLES,
            "items": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
        },
        "relation": {
            "type": ["object", "null"],
            "required": ["kind", "from_role", "to_role"],
            "additionalProperties": False,
            "properties": {
                "kind": {"enum": list(RELATIONSHIP_KINDS)},
                "from_role": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_ID_LENGTH,
                },
                "to_role": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_ID_LENGTH,
                },
            },
        },
    },
}

#: The canonical bounded scene-package payload contract.
PACKAGE_PAYLOAD_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ScenePackagePayload",
    "type": "object",
    "required": [
        "display_name",
        "source_id",
        "quest",
        "roles",
        "relationships",
        "knowledge",
        "encounters",
        "dialogue",
        "commissions",
    ],
    "additionalProperties": False,
    "properties": {
        "display_name": {"type": "string", "minLength": 1, "maxLength": 80},
        "source_id": {
            "type": ["string", "null"],
            "minLength": 1,
            "maxLength": 255,
        },
        "quest": {"type": "object"},
        "roles": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ROLES,
            "items": _ROLE,
        },
        "relationships": {
            "type": "array",
            "maxItems": MAX_ROLES,
            "items": {
                "type": "object",
                "required": ["from_role", "to_role", "kind"],
                "additionalProperties": False,
                "properties": {
                    "from_role": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "to_role": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "kind": {"enum": list(RELATIONSHIP_KINDS)},
                },
            },
        },
        "knowledge": {
            "type": "array",
            "maxItems": MAX_CLAIMS,
            "items": {
                "type": "object",
                "required": ["role_id", "claim_id", "text", "provenance"],
                "additionalProperties": False,
                "properties": {
                    "role_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "claim_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "text": {"type": "string", "minLength": 1, "maxLength": 200},
                    "provenance": {
                        "type": "object",
                        "required": ["kind", "ref"],
                        "additionalProperties": False,
                        "properties": {
                            "kind": {"enum": ["role_owner"]},
                            "ref": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                        },
                    },
                },
            },
        },
        "encounters": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ENCOUNTERS,
            "items": {
                "type": "object",
                "required": ["scene_id", "role_ids", "locator", "prerequisites"],
                "additionalProperties": False,
                "properties": {
                    "scene_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "role_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_ROLES,
                        "items": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    },
                    "locator": _LOCATOR,
                    "prerequisites": {
                        "type": "array",
                        "maxItems": 4,
                        "items": _CONDITION,
                    },
                },
            },
        },
        "dialogue": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ROLES,
            "items": {
                "type": "object",
                "required": ["role_id", "initial_phase", "phases"],
                "additionalProperties": False,
                "properties": {
                    "role_id": {"type": "string", "minLength": 1, "maxLength": MAX_ID_LENGTH},
                    "initial_phase": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_ID_LENGTH,
                    },
                    "phases": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_PHASES,
                        "items": _PHASE,
                    },
                },
            },
        },
        #: The package's distinct role-issued commission declarations. Empty
        #: for a guild-branch package; otherwise at least one entry, and the
        #: quest's declared issuer role must be among them (escort design §7).
        "commissions": {
            "type": "array",
            "maxItems": MAX_ROLES,
            "items": {
                "type": "object",
                "required": ["role_id", "issuer_content_key"],
                "additionalProperties": False,
                "properties": {
                    "role_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_ID_LENGTH,
                    },
                    "issuer_content_key": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 60,
                        "pattern": "^[^0-9][^:]*$",
                    },
                },
            },
        },
        #: The optional explicit exclusive outcome groups. A group's ``result``
        #: is the concrete final escort predicate and ``alternatives`` the
        #: distinct commission definition keys it obsoletes; story-thread
        #: identity alone implies no exclusivity (escort design §7).
        "outcome_groups": {
            "type": "array",
            "maxItems": MAX_ROLES,
            "items": {
                "type": "object",
                "required": ["group_id", "result", "alternatives"],
                "additionalProperties": False,
                "properties": {
                    "group_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_ID_LENGTH,
                    },
                    "result": _ESCORT_RESULT,
                    "alternatives": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_ROLES,
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_ID_LENGTH,
                        },
                    },
                },
            },
        },
    },
}


def package_schema_errors(payload: Any) -> tuple[str, ...]:
    """Return the structural failures of a proposed package payload.

    A structural failure is a bounded-shape violation (an unknown key, a missing
    required key, an out-of-vocabulary layer or effect verb, an over-bound
    string); registry references and ownership are the deterministic boundary's
    semantic contract and are not resolved here.
    """
    from jsonschema import Draft7Validator

    validator = Draft7Validator(PACKAGE_PAYLOAD_SCHEMA)
    errors = []
    for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{location}: {error.message}")
    return tuple(errors)


__all__ = [
    "DESTINATION_LAYERS",
    "EFFECT_VERBS",
    "OBJECTIVE_KINDS",
    "PACKAGE_PAYLOAD_SCHEMA",
    "RELATIONSHIP_KINDS",
    "package_schema_errors",
]