"""The guardrail vocabulary: output schema, semantic validators, and hooks.

The ``scenario_director`` raw-wire jsonschema, every semantic validator the
guardrail runs after schema acceptance, the sentinel degrade fallback, and the
identity-referenced :class:`GuardrailHooks` bundle installed by
``register_scenario_director`` in :mod:`.generation` all live here; the gate
compares these objects by identity, so this module is their single owner.

The boundary contract (``tests/test_ai_transport_contract.py``): this module
imports no state writer, no typeclass, no live transport, and no socket. It
reads only the immutable ``world.lore`` registries and the side-effect-free
shared ``world.quests.characterization`` helper (read-only-rule exemption, D3).
"""

from __future__ import annotations

from typing import Any

from world.ai.guardrail import GuardrailHooks
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.quests.characterization import (
    characterize_errors,
    duplicate_display_name_errors,
    duplicate_stable_key_errors,
    race_lifespan_upper_bound,
)

from world.ai.scenario_director.blueprints import (
    _CJK_END,
    _CJK_START,
    _TEMPLATE_PLACEHOLDER_RE,
    MAX_NAME_LENGTH,
    MAX_SCENE_SENTENCE_LENGTH,
    BlueprintLocationLayer,
    BlueprintObjectiveKind,
    BlueprintQuestType,
)


class ScenarioDirectorClientRequiredError(TypeError):
    """Raised when ``generate_quest_blueprint`` is called with an explicit ``None`` client."""


class ScenarioDirectorNotRegisteredError(RuntimeError):
    """Raised when ``generate_quest_blueprint`` runs before the layer hooks are installed."""


class ScenarioDirectorTemplateError(RuntimeError):
    """Raised when no template in the pool fits the request context."""


SCENARIO_DIRECTOR_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["name", "quest_type", "rank", "issuer", "stages", "reward", "failure"],
    "properties": {
        "name": {"type": "string"},
        "quest_type": {
            "type": "string",
            "enum": [quest_type.value for quest_type in BlueprintQuestType],
        },
        "rank": {"type": "string"},
        "issuer": {"type": "string"},
        "stages": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["index", "objective"],
                "properties": {
                    "index": {"type": "integer", "minimum": 0},
                    "objective": {
                        "type": "object",
                        "required": ["kind"],
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": [
                                    kind.value for kind in BlueprintObjectiveKind
                                ],
                            },
                            "quantity": {"type": "integer", "minimum": 1},
                            "monster_tier": {"type": ["string", "null"]},
                            "item_key": {"type": ["string", "null"]},
                        },
                    },
                    "location_req": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "required": ["layer"],
                                "properties": {
                                    "layer": {
                                        "type": "string",
                                        "enum": [
                                            layer.value
                                            for layer in BlueprintLocationLayer
                                        ],
                                    },
                                    "archetype": {"type": ["string", "null"]},
                                    "anchor_key": {"type": ["string", "null"]},
                                    "anchor_near": {"type": ["string", "null"]},
                                    "xyz": {
                                        "type": ["array", "null"],
                                        "items": [
                                            {"type": "integer"},
                                            {"type": "integer"},
                                            {"type": "string"},
                                        ],
                                        "minItems": 3,
                                        "maxItems": 3,
                                    },
                                    "scene_sentence": {"type": ["string", "null"]},
                                },
                            },
                        ]
                    },
                    "npc_req": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["role", "tier", "display_name", "title"],
                            "properties": {
                                "role": {"type": "string"},
                                "tier": {"type": "string"},
                                "disposition": {"type": ["string", "null"]},
                                "display_name": {"type": ["string", "null"]},
                                "title": {"type": ["string", "null"]},
                                "age": {"type": ["integer", "null"], "minimum": 0},
                                "apparent_age": {
                                    "type": ["integer", "null"],
                                    "minimum": 0,
                                },
                                "portrait": {
                                    "type": ["object", "null"],
                                    "required": ["stable_key"],
                                    "properties": {
                                        "stable_key": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                                "background": {"type": ["string", "null"]},
                                "persona": {
                                    "type": ["object", "null"],
                                    "properties": {
                                        "personality": {"type": "string"},
                                        "life_story": {"type": "string"},
                                        "habit": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                            },
                        },
                    },
                },
            },
        },
        "reward": {
            "type": "object",
            "required": ["copper", "items", "merit"],
            "properties": {
                "copper": {"type": "integer", "minimum": 0},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["item_key", "quantity"],
                        "properties": {
                            "item_key": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                    },
                },
                "merit": {"type": "integer", "minimum": 0},
            },
        },
        "failure": {
            "type": "object",
            "required": ["deadline_hours", "conditions"],
            "properties": {
                "deadline_hours": {"type": ["integer", "null"], "minimum": 1},
                "conditions": {"type": "array", "maxItems": 0},
            },
        },
    },
}

_SCENARIO_DIRECTOR_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the template draw."""
    return _SCENARIO_DIRECTOR_DEGRADED


def _stages(parsed: Any) -> list[Any]:
    if not isinstance(parsed, dict):
        return []
    stages = parsed.get("stages")
    if not isinstance(stages, list):
        return []
    return stages


def _validate_rank_known(parsed: Any) -> list[str]:
    rank = parsed.get("rank") if isinstance(parsed, dict) else None
    if not isinstance(rank, str) or rank not in GUILD_RANK_REGISTRY:
        return [f"quest rank {rank!r} is not in GUILD_RANK_REGISTRY"]
    return []


def _validate_reward_in_band(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    rank = parsed.get("rank")
    reward = parsed.get("reward")
    guild_rank = GUILD_RANK_REGISTRY.get(rank) if isinstance(rank, str) else None
    if guild_rank is None or not isinstance(reward, dict):
        return errors
    copper = reward.get("copper")
    if isinstance(copper, bool) or not isinstance(copper, int):
        errors.append("reward copper must be an integer")
    else:
        band_floor = guild_rank.reward_min_copper
        band_ceiling = guild_rank.reward_max_copper
        if copper < band_floor or (band_ceiling is not None and copper > band_ceiling):
            errors.append(
                f"reward copper {copper} is outside {rank} rank "
                f"band [{band_floor}, {band_ceiling}]"
            )
    merit = reward.get("merit")
    if isinstance(merit, bool) or not isinstance(merit, int) or merit < 0:
        errors.append("reward merit must be a non-negative integer")
    return errors


def _validate_reward_items_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    reward = parsed.get("reward")
    if not isinstance(reward, dict):
        return errors
    items = reward.get("items")
    if not isinstance(items, list):
        return errors
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("reward items must be objects")
            continue
        item_key = item.get("item_key")
        if not isinstance(item_key, str) or item_key not in ITEM_REGISTRY:
            errors.append(f"unknown reward item {item_key!r}")
        quantity = item.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            errors.append(
                f"reward item {item_key!r} quantity must be a positive integer"
            )
        if isinstance(item_key, str):
            if item_key in seen:
                errors.append(f"duplicate reward item key {item_key!r}")
            seen.add(item_key)
    return errors


def _validate_archetype_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict):
            continue
        archetype = location.get("archetype")
        if archetype is not None and (
            not isinstance(archetype, str)
            or archetype not in SCENE_ARCHETYPE_REGISTRY
        ):
            errors.append(f"stage {index} unknown archetype {archetype!r}")
    return errors


def _validate_npc_tier_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        requirements = stage.get("npc_req")
        if not isinstance(requirements, list):
            continue
        for requirement in requirements:
            if not isinstance(requirement, dict):
                errors.append(f"stage {index} npc_req entries must be objects")
                continue
            tier = requirement.get("tier")
            if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
                errors.append(f"stage {index} unknown NPC tier {tier!r}")
    return errors


def _validate_npc_characterization(parsed: Any) -> list[str]:
    """Validate every ``npc_req`` entry's optional characterization fields.

    Delegates per-entry age/name/key rules and the cross-entry duplicate
    ``stable_key`` agreement rule to the shared ``world.quests.characterization``
    helper -- the single rule source both this guardrail and the deterministic
    compiler call (design D3). The race-lifespan upper bound is resolved
    through the tier's ``race_key``; an unknown tier is reported by
    ``_validate_npc_tier_known``, so this validator skips it to avoid a second
    (redundant) diagnostic.
    """
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        requirements = stage.get("npc_req")
        if not isinstance(requirements, list):
            continue
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            entries.append(requirement)
            tier = requirement.get("tier")
            if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
                continue
            for message in characterize_errors(
                requirement,
                lifespan_upper_bound=race_lifespan_upper_bound(tier),
            ):
                errors.append(f"stage {index} {message}")
    errors.extend(duplicate_stable_key_errors(entries))
    errors.extend(duplicate_display_name_errors(entries))
    return errors


def _validate_monster_tier_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict) or objective.get("kind") != "defeat":
            continue
        monster_tier = objective.get("monster_tier")
        if monster_tier is not None and (
            not isinstance(monster_tier, str)
            or monster_tier not in MONSTER_TIER_REGISTRY
        ):
            errors.append(f"stage {index} unknown monster tier {monster_tier!r}")
    return errors


def _validate_issuer_known(parsed: Any) -> list[str]:
    issuer = parsed.get("issuer") if isinstance(parsed, dict) else None
    if not isinstance(issuer, str) or issuer not in GUILD_BRANCH_REGISTRY:
        return [f"issuer branch {issuer!r} is not in GUILD_BRANCH_REGISTRY"]
    return []


def _validate_stage_indices_contiguous(parsed: Any) -> list[str]:
    indices = [
        stage.get("index")
        for stage in _stages(parsed)
        if isinstance(stage, dict)
    ]
    if indices != list(range(len(indices))):
        return [f"stage indices must be contiguous starting at zero, got {indices}"]
    return []


def _validate_deadline_valid(parsed: Any) -> list[str]:
    failure = parsed.get("failure") if isinstance(parsed, dict) else None
    if not isinstance(failure, dict):
        return []
    deadline = failure.get("deadline_hours")
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, int) or deadline < 1
    ):
        return ["failure.deadline_hours must be None or a positive integer"]
    return []


def _is_cjk(text: str) -> bool:
    return any(_CJK_START <= ch <= _CJK_END for ch in text)


def _validate_strings_bounded_cjk(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    name = parsed.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("blueprint name is empty or whitespace-only")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(f"blueprint name exceeds the {MAX_NAME_LENGTH}-character cap")
    elif not _is_cjk(name):
        errors.append("blueprint name contains no CJK Unified Ideograph")
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict):
            continue
        sentence = location.get("scene_sentence")
        if sentence is None:
            continue
        if not isinstance(sentence, str) or not sentence.strip():
            errors.append(f"stage {index} scene_sentence is empty or whitespace-only")
        elif len(sentence) > MAX_SCENE_SENTENCE_LENGTH:
            errors.append(
                f"stage {index} scene_sentence exceeds the "
                f"{MAX_SCENE_SENTENCE_LENGTH}-character cap"
            )
        elif not _is_cjk(sentence):
            errors.append(f"stage {index} scene_sentence contains no CJK ideograph")
    return errors


def _validate_anchor_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict) or location.get("layer") != "anchor":
            continue
        anchor_key = location.get("anchor_key")
        if not isinstance(anchor_key, str) or anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            errors.append(
                f"stage {index} ANCHOR locator references unplaced anchor {anchor_key!r}"
            )
    return errors


def _validate_defeat_selector(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict) or objective.get("kind") != "defeat":
            continue
        has_tier = objective.get("monster_tier") is not None
        npc_req = stage.get("npc_req")
        has_npc = isinstance(npc_req, list) and bool(npc_req)
        if has_tier == has_npc:
            errors.append(
                f"stage {index} DEFEAT must declare exactly one of a known "
                "monster_tier or a non-empty npc_req"
            )
    return errors


def _validate_scene_bound_rules(parsed: Any) -> list[str]:
    """Enforce the shared scene-bound rules the compiler also enforces (D5).

    Occupant-bearing scenes (any ``npc_req``) must be instance-layer so spawned
    entities always live in a reclaimable instance room; an ESCORT stage is
    refused entirely until a protected-entity binding flow exists; a
    bound-target DEFEAT quantity must not exceed its ``npc_req`` count; and
    ``anchor_near`` must name a placed anchor.
    """
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        objective = stage.get("objective")
        npc_req = stage.get("npc_req")
        layer = location.get("layer") if isinstance(location, dict) else None
        has_npc = isinstance(npc_req, list) and bool(npc_req)
        is_escort = isinstance(objective, dict) and objective.get("kind") == "escort"
        if is_escort:
            errors.append(
                f"stage {index} declares an ESCORT objective, which cannot be "
                "published until a protected-entity binding flow exists"
            )
        if has_npc and layer != "instance":
            errors.append(
                f"stage {index} declares NPC requirements outside an "
                "instance-layer destination; occupant-bearing scenes must be "
                "instances"
            )
        if (
            isinstance(objective, dict)
            and objective.get("kind") == "defeat"
            and objective.get("monster_tier") is None
            and has_npc
        ):
            quantity = objective.get("quantity", 1)
            if (
                not isinstance(quantity, bool)
                and isinstance(quantity, int)
                and quantity > len(npc_req)
            ):
                errors.append(
                    f"stage {index} bound DEFEAT quantity {quantity} exceeds "
                    f"the number of npc_req entries {len(npc_req)}"
                )
        if isinstance(location, dict):
            anchor_near = location.get("anchor_near")
            if anchor_near is not None and (
                not isinstance(anchor_near, str)
                or anchor_near not in ANCHOR_PLACEMENT_REGISTRY
            ):
                errors.append(
                    f"stage {index} anchor_near {anchor_near!r} is not a placed "
                    "anchor in ANCHOR_PLACEMENT_REGISTRY"
                )
    return errors


def _validate_objective_selectors(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict):
            continue
        kind = objective.get("kind")
        if kind == "acquire":
            if objective.get("item_key") is None:
                errors.append(f"stage {index} ACQUIRE requires a known item_key")
            if objective.get("monster_tier") is not None:
                errors.append(f"stage {index} ACQUIRE cannot declare a monster_tier")
        elif kind in ("reach_location", "escort"):
            if stage.get("location_req") is None:
                errors.append(
                    f"stage {index} {kind} requires a location_req destination"
                )
            if objective.get("monster_tier") is not None:
                errors.append(
                    f"stage {index} {kind} cannot declare a monster_tier"
                )
            quantity = objective.get("quantity", 1)
            if (
                not isinstance(quantity, bool)
                and isinstance(quantity, int)
                and quantity != 1
            ):
                errors.append(
                    f"stage {index} {kind} quantity must be exactly 1; "
                    "arrival observation cannot accumulate repeated visits"
                )
    return errors


def _validate_no_template_placeholder(parsed: Any) -> list[str]:
    search_text = ""
    if isinstance(parsed, dict):
        name = parsed.get("name")
        if isinstance(name, str):
            search_text += name
        for stage in _stages(parsed):
            if not isinstance(stage, dict):
                continue
            location = stage.get("location_req")
            if isinstance(location, dict):
                sentence = location.get("scene_sentence")
                if isinstance(sentence, str):
                    search_text += sentence
    if _TEMPLATE_PLACEHOLDER_RE.search(search_text):
        return ["blueprint echoes deterministic template-placeholder formatting syntax"]
    return []


_VALIDATORS: dict[str, Any] = {
    "rank_known": _validate_rank_known,
    "reward_in_band": _validate_reward_in_band,
    "reward_items_known": _validate_reward_items_known,
    "archetype_known": _validate_archetype_known,
    "npc_tier_known": _validate_npc_tier_known,
    "npc_characterization": _validate_npc_characterization,
    "monster_tier_known": _validate_monster_tier_known,
    "anchor_known": _validate_anchor_known,
    "defeat_selector": _validate_defeat_selector,
    "scene_bound_rules": _validate_scene_bound_rules,
    "objective_selectors": _validate_objective_selectors,
    "issuer_known": _validate_issuer_known,
    "stage_indices_contiguous": _validate_stage_indices_contiguous,
    "deadline_valid": _validate_deadline_valid,
    "strings_bounded_cjk": _validate_strings_bounded_cjk,
    "no_template_placeholder": _validate_no_template_placeholder,
}

_HOOKS = GuardrailHooks(
    layer="scenario_director",
    fallback=_degrade_fallback,
    validators=_VALIDATORS,
)
