"""Canonical serialization and the content-digest definition key.

The single canonical shapes used both for the ``_definition_key`` content
digest and for equality against a previously registered spawn-requirement
entry, so two compilations of identical scenes compare equal by
construction. Leaf of the ``world.quests.compile`` package: pure functions
over the frozen contract values.
"""

import hashlib
import json
from typing import Any

from world.quests.compile.contracts import (
    StageNpcCharacterization,
    StageSpawnRequirement,
)


def _definition_key(
    definition_fields: dict[str, Any],
    stage_requirements: tuple[StageSpawnRequirement, ...],
) -> str:
    """Return the stable content-digest key for a compiled definition.

    ``sha256`` over the canonical serialization of the definition's own fields
    **plus the canonical serialization of the compiled per-stage spawn
    requirements**, hex-prefixed. Equal content always yields an equal key;
    different content never collides. Folding the scene requirements into the
    digest means two blueprints with identical runtime stages but different
    scenes (archetype, ``anchor_near``, ``scene_sentence``, or ``npc_reqs``)
    get different keys, so one can never silently overwrite the other's
    spawn-requirement entry. Reward and issuer are offer-level and excluded, so
    two blueprints with identical stages but different rewards share a
    definition key and surface as offer conflicts through
    ``register_generated_quest``.
    """
    canonical = json.dumps(
        {
            "definition": definition_fields,
            "stage_requirements": [
                _stage_requirement_canonical(requirement)
                for requirement in stage_requirements
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"ai_{digest[:16]}"


def _npc_req_canonical(
    entry: tuple[str, str, str | None],
    characterization: StageNpcCharacterization | None,
) -> dict[str, Any]:
    """Serialize one ``npc_req`` entry into a canonical JSON-safe dict.

    The base shape (role/tier/disposition) is always present; the optional
    characterization fields are included only when declared, so a field-less
    blueprint contributes a byte-identical digest to today's output while two
    blueprints differing only in characterization stay distinguishable.
    """
    role, tier, disposition = entry
    canonical: dict[str, Any] = {
        "role": role,
        "tier": tier,
        "disposition": disposition,
    }
    if characterization is not None:
        if characterization.display_name is not None:
            canonical["display_name"] = characterization.display_name
        if characterization.title is not None:
            canonical["title"] = characterization.title
        if characterization.age is not None:
            canonical["age"] = characterization.age
        if characterization.apparent_age is not None:
            canonical["apparent_age"] = characterization.apparent_age
        if characterization.portrait_stable_key is not None:
            canonical["portrait"] = {
                "stable_key": characterization.portrait_stable_key
            }
        if characterization.background is not None:
            canonical["background"] = characterization.background
        if characterization.persona:
            canonical["persona"] = dict(characterization.persona)
        if characterization.combat_traits:
            canonical["combat_traits"] = list(characterization.combat_traits)
    return canonical


def _stage_requirement_canonical(requirement: StageSpawnRequirement) -> dict[str, Any]:
    """Serialize one ``StageSpawnRequirement`` into a canonical JSON-safe dict.

    This is the single canonical shape used both for the definition content
    digest and for equality against a previously registered requirement entry,
    so two compilations of identical scenes compare equal by construction.
    """
    location = requirement.location
    return {
        "index": requirement.index,
        "objective_kind": requirement.objective_kind.value,
        "location": (
            None
            if location is None
            else {
                "kind": location.kind.value,
                "anchor_key": location.anchor_key,
                "xyz": None if location.xyz is None else list(location.xyz),
            }
        ),
        "archetype": requirement.archetype,
        "anchor_near": requirement.anchor_near,
        "scene_sentence": requirement.scene_sentence,
        "npc_reqs": [
            _npc_req_canonical(
                entry,
                requirement.characterizations[position]
                if position < len(requirement.characterizations)
                else None,
            )
            for position, entry in enumerate(requirement.npc_reqs)
        ],
    }
