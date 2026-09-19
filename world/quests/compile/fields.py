"""Shared payload-field validators for the compile boundary.

The leaf validation helpers of the ``world.quests.compile`` package: string,
mapping, integer, reward, location, characterization, scene-field, and
objective checks. Every constraint mirrors the ``scenario_director`` guardrail
rule it re-checks, against the same ``world.lore`` registries, so the two
sides cannot drift; violations raise through the shared ``_reject``.
"""

from typing import Any

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.quests.characterization import (
    characterize_errors,
    race_lifespan_upper_bound,
)
from world.quests.compile.contracts import (
    QuestCompileError,
    StageNpcCharacterization,
    _DESTINATION_KIND_BY_VALUE,
    _OBJECTIVE_KIND_BY_VALUE,
    _TEMPLATE_PLACEHOLDER_RE,
    _has_cjk,
    _reject,
)
from world.quests.definitions import (
    KNOWN_GRID_MAP_KEYS,
    DestinationKind,
    ObjectiveKind,
    QuestObjective,
    RoomLocator,
)
from world.rules.guild_offers import (
    ItemQuantity,
    QuestReward,
)


def _validate_strings(
    stage_index: int | None,
    field: str,
    value: Any,
    max_length: int,
    *,
    required: bool,
) -> None:
    if not isinstance(value, str) or not value.strip():
        if required:
            _reject(f"{field} must be a non-empty string")
        return
    if len(value) > max_length:
        _reject(f"{field} exceeds the {max_length}-character cap")
    if not _has_cjk(value):
        _reject(f"{field} contains no CJK Unified Ideograph and is not Traditional Chinese")
    if _TEMPLATE_PLACEHOLDER_RE.search(value):
        _reject(f"{field} echoes deterministic template-placeholder formatting syntax")


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _reject(f"{field} must be an object")
    return value


def _require_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _reject(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        _reject(f"{field} must be at least {minimum}")
    return value


def _validate_reward(
    rank: str,
    reward_payload: Any,
) -> QuestReward:
    reward = _require_mapping(reward_payload, "reward")
    copper = _require_int(reward.get("copper"), "reward.copper", minimum=0)
    merit = _require_int(reward.get("merit"), "reward.merit", minimum=0)

    guild_rank = GUILD_RANK_REGISTRY.get(rank)
    if guild_rank is None:
        _reject(f"unknown quest rank {rank!r}")
    band_floor = guild_rank.reward_min_copper
    band_ceiling = guild_rank.reward_max_copper
    if copper < band_floor:
        _reject(f"reward copper {copper} is below {rank} rank minimum {band_floor}")
    if band_ceiling is not None and copper > band_ceiling:
        _reject(f"reward copper {copper} is above {rank} rank maximum {band_ceiling}")

    items = reward.get("items")
    if not isinstance(items, list):
        _reject("reward.items must be an array")
    quantities: list[ItemQuantity] = []
    seen: set[str] = set()
    for position, item in enumerate(items):
        item = _require_mapping(item, f"reward.items[{position}]")
        item_key = item.get("item_key")
        if not isinstance(item_key, str) or not item_key:
            _reject(f"reward.items[{position}].item_key must be a non-empty string")
        if item_key not in ITEM_REGISTRY:
            _reject(f"unknown reward item {item_key!r}")
        quantity = _require_int(
            item.get("quantity"), f"reward.items[{position}].quantity", minimum=1
        )
        if item_key in seen:
            _reject(f"duplicate reward item key {item_key!r}")
        seen.add(item_key)
        quantities.append(ItemQuantity(item_key, quantity))
    return QuestReward(copper=copper, items=tuple(quantities), merit=merit)


def _compile_location(location_payload: Any) -> RoomLocator:
    location = _require_mapping(location_payload, "location_req")
    layer = location.get("layer")
    if not isinstance(layer, str) or layer not in _DESTINATION_KIND_BY_VALUE:
        _reject(f"unknown destination layer {layer!r}; wilderness is not representable")
    if layer == "wilderness":
        _reject("wilderness destinations cannot be declared")

    if layer == "anchor":
        anchor_key = location.get("anchor_key")
        if not isinstance(anchor_key, str) or not anchor_key:
            _reject("ANCHOR locator requires a non-empty anchor_key")
        if anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(f"anchor {anchor_key!r} has no reachable AnchorRoom in placement registry")
        return RoomLocator(DestinationKind.ANCHOR, anchor_key=anchor_key)

    if layer == "grid":
        xyz = location.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3:
            _reject("GRID locator requires an [x, y, z] coordinate list")
        x, y, z = xyz
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
            or not isinstance(z, str)
            or not z
        ):
            _reject("GRID locator requires integer x/y and a non-empty map key z")
        if z not in KNOWN_GRID_MAP_KEYS:
            _reject(f"grid map key {z!r} is not known to the xyzgrid")
        return RoomLocator(DestinationKind.GRID, xyz=(x, y, z))

    if layer == "instance":
        if location.get("anchor_key") is not None or location.get("xyz") is not None:
            _reject("BOUND_INSTANCE locator cannot carry static location fields")
        return RoomLocator(DestinationKind.BOUND_INSTANCE)

    _reject(f"unknown destination layer {layer!r}")  # pragma: no cover


def _compile_characterization(
    requirement: dict[str, Any],
) -> StageNpcCharacterization | None:
    """Build one occupant's frozen characterization value from a raw entry.

    Every accepted entry carries the required authored identity (the shared
    helper rejected a missing ``display_name``/``title`` before this point), so
    the result is never ``None`` (npc-title-authored-identities D5). The
    optional authored persona/background flavor is preserved in deterministic
    field order (fix-custom-creation-information-and-background D7).
    """
    portrait = requirement.get("portrait")
    stable_key = None
    if isinstance(portrait, dict):
        stable_key = portrait.get("stable_key")
    background = requirement.get("background")
    persona = requirement.get("persona")
    persona_prose = ()
    if isinstance(persona, dict):
        persona_prose = tuple(
            (field, persona[field])
            for field in ("personality", "life_story", "habit")
            if isinstance(persona.get(field), str) and persona[field].strip()
        )
    raw_combat_traits = requirement.get("combat_traits")
    combat_traits: tuple[str, ...] = ()
    if raw_combat_traits is not None:
        from world.rules.traits import validate_combat_traits

        try:
            combat_traits = tuple(validate_combat_traits(raw_combat_traits))
        except ValueError as error:
            raise QuestCompileError(
                f"invalid combat_traits in characterization: {error}"
            ) from error
    return StageNpcCharacterization(
        display_name=requirement.get("display_name"),
        title=requirement.get("title"),
        age=requirement.get("age"),
        apparent_age=requirement.get("apparent_age"),
        portrait_stable_key=stable_key,
        background=background if isinstance(background, str) else None,
        persona=persona_prose,
        combat_traits=combat_traits,
    )


def _validate_scene_fields(
    stage_index: int,
    location_payload: Any,
    npc_req_payload: Any,
) -> tuple[
    str | None,
    str | None,
    str | None,
    tuple[tuple[str, str, str | None], ...],
    tuple[StageNpcCharacterization | None, ...],
]:
    """Validate archetype, anchor hint, scene sentence, and NPC requirements."""
    archetype = None
    anchor_near = None
    scene_sentence = None
    if isinstance(location_payload, dict):
        archetype = location_payload.get("archetype")
        if archetype is not None and (
            not isinstance(archetype, str)
            or archetype not in SCENE_ARCHETYPE_REGISTRY
        ):
            _reject(f"stage {stage_index} unknown archetype {archetype!r}")
        anchor_near = location_payload.get("anchor_near")
        if anchor_near is not None and not isinstance(anchor_near, str):
            _reject(f"stage {stage_index} anchor_near must be a string or None")
        if anchor_near is not None and anchor_near not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(
                f"stage {stage_index} anchor_near {anchor_near!r} "
                "is not a placed anchor in ANCHOR_PLACEMENT_REGISTRY"
            )
        scene_sentence = location_payload.get("scene_sentence")
        _validate_strings(
            stage_index,
            f"stage {stage_index} scene_sentence",
            scene_sentence,
            500,
            required=False,
        )

    if not isinstance(npc_req_payload, list):
        _reject(f"stage {stage_index} npc_req must be an array")
    npc_reqs: list[tuple[str, str, str | None]] = []
    characterizations: list[StageNpcCharacterization | None] = []
    for position, requirement in enumerate(npc_req_payload):
        requirement = _require_mapping(
            requirement, f"stage {stage_index} npc_req[{position}]"
        )
        role = requirement.get("role")
        if not isinstance(role, str) or not role:
            _reject(f"stage {stage_index} npc_req[{position}].role must be a string")
        tier = requirement.get("tier")
        if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
            _reject(f"stage {stage_index} npc_req[{position}] unknown tier {tier!r}")
        disposition = requirement.get("disposition")
        if disposition is not None and not isinstance(disposition, str):
            _reject(
                f"stage {stage_index} npc_req[{position}].disposition "
                "must be a string or None"
            )
        for message in characterize_errors(
            requirement,
            lifespan_upper_bound=race_lifespan_upper_bound(tier),
        ):
            _reject(
                f"stage {stage_index} npc_req[{position}] {message}"
            )
        npc_reqs.append((role, tier, disposition))
        characterizations.append(_compile_characterization(requirement))
    return (
        archetype,
        anchor_near,
        scene_sentence,
        tuple(npc_reqs),
        tuple(characterizations),
    )


def _compile_objective(
    stage_index: int,
    objective_payload: Any,
    location: RoomLocator | None,
    has_npc_reqs: bool,
) -> QuestObjective:
    objective = _require_mapping(objective_payload, f"stage {stage_index}.objective")
    kind_value = objective.get("kind")
    if not isinstance(kind_value, str) or kind_value not in _OBJECTIVE_KIND_BY_VALUE:
        _reject(f"stage {stage_index} unknown objective kind {kind_value!r}")
    kind = _OBJECTIVE_KIND_BY_VALUE[kind_value]
    quantity = _require_int(
        objective.get("quantity", 1), f"stage {stage_index}.objective.quantity", minimum=1
    )

    if kind is ObjectiveKind.DEFEAT:
        monster_tier = objective.get("monster_tier")
        has_tier = monster_tier is not None
        if has_tier == has_npc_reqs:
            _reject(
                f"stage {stage_index} DEFEAT objective must declare exactly one of "
                "a known monster_tier or a non-empty npc_req"
            )
        if has_tier:
            if not isinstance(monster_tier, str) or monster_tier not in MONSTER_TIER_REGISTRY:
                _reject(f"stage {stage_index} unknown monster tier {monster_tier!r}")
            return QuestObjective(
                kind=kind,
                quantity=quantity,
                monster_tier=monster_tier,
            )
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            requires_bound_targets=True,
        )

    if kind is ObjectiveKind.ACQUIRE:
        item_key = objective.get("item_key")
        if not isinstance(item_key, str) or not item_key:
            _reject(f"stage {stage_index} ACQUIRE objective requires a known item_key")
        if item_key not in ITEM_REGISTRY:
            _reject(f"stage {stage_index} ACQUIRE references unknown item {item_key!r}")
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            item_key=item_key,
        )

    if kind in (ObjectiveKind.REACH, ObjectiveKind.ESCORT):
        if location is None:
            _reject(f"stage {stage_index} {kind.value} objective requires a destination")
        if quantity != 1:
            _reject(
                f"stage {stage_index} {kind.value} objective quantity must be "
                "exactly 1; arrival observation cannot accumulate repeated visits"
            )
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            destination=location,
        )

    _reject(f"stage {stage_index} unknown objective kind {kind_value!r}")  # pragma: no cover
