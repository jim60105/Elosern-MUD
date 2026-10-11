"""Deterministic SceneBuilder: requirements -> prototype -> spawn (design §7.2).

Change 21's materializer lives in the deterministic quest-lifecycle package,
not ``world/ai/``: it spawns rooms and occupants and binds quest state, so it is
a state writer and can never live in the generative layer. It consumes a
stage's registered spawn requirements only as plain validated data
(``StageSpawnRequirement`` read through ``scene_requirements_for``), never a
proposal object, and it honors §7.2's anti-hallucination rule by construction:
requirements carry only registry keys (archetype, tier, anchor, layer); every
stored numeric stat comes from the immutable lore tables; and occupant class
lineage is selected only from ``SCENE_OCCUPANT_PROTOTYPE_WHITELIST``.

Materialization is lazy (triggered by the player's ``進入`` action, not at
acceptance), atomic (one outer ``transaction.atomic()`` composes the room, the
exit pair, the occupants, their ownership, and the quest binding), and
idempotent (an already-bound current stage returns the existing binding and
spawns nothing). Permanent-layer stages are located only and never given
spawned occupants (D5).
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.observability import log_warn
from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity
from typeclasses.rooms import AnchorRoom, GridRoom, InstanceRoom
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.maps.instance import register_owned_entity, spawn_instance_room
from world.quests.binding import bind_stage_runtime
from world.quests.compile import scene_requirements_for
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.materializer import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    RoleSpawn,
    SceneBuilderError,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    schedule_occupant_portraits as _schedule_occupant_portraits,
    scene_name as _materializer_scene_name,
    spawn_monster as _spawn_monster,
    spawn_role_actor,
    validate_characterization as _validate_characterization,
    validate_occupant_parent as _validate_occupant_parent,
)
from world.quests.runtime import (
    QuestState,
    definition_for,
    find_record,
    read_records,
)

RETURN_EXIT_KEY = "返回"


@dataclass(frozen=True)
class SceneMaterialization:
    """The committed result of one stage materialization."""

    room: Any
    record: Any
    flavor_context: dict[str, str] | None = None


def _scene_name(archetype_key: str | None) -> str:
    """Return one scene archetype's display name through the shared materializer."""
    return _materializer_scene_name(archetype_key)


def _scene_exit_key(archetype_key: str | None) -> str:
    return _scene_name(archetype_key)


def _revalidate_keys(requirement: Any) -> None:
    """Re-validate every registry key before any spawn (defense in depth)."""
    if requirement.archetype is not None and requirement.archetype not in SCENE_ARCHETYPE_REGISTRY:
        raise SceneBuilderSpawnError(
            f"unknown scene archetype {requirement.archetype!r}"
        )
    if (
        requirement.anchor_near is not None
        and requirement.anchor_near not in ANCHOR_PLACEMENT_REGISTRY
    ):
        raise SceneBuilderSpawnError(
            f"unknown anchor {requirement.anchor_near!r}"
        )
    for position, (role, tier_key, _disposition) in enumerate(requirement.npc_reqs):
        if tier_key not in NPC_TIER_REGISTRY:
            raise SceneBuilderSpawnError(f"unknown NPC tier {tier_key!r}")
        characterizations = getattr(requirement, "characterizations", ())
        characterization = (
            characterizations[position]
            if position < len(characterizations)
            else None
        )
        # The one shared characterization gate (world.quests.materializer): a
        # forged requirement cannot bypass the age-bounds rule, the authored
        # identity invariant, or the compact-card contract on any spawn path.
        _validate_characterization(characterization, role, tier_key)


def _spawn_scene_room(actor, origin_room: Any, requirement: Any) -> InstanceRoom:
    name = _scene_name(requirement.archetype)
    room = spawn_instance_room(
        origin_room,
        {"prototype_parent": "instance_room", "key": name},
        exit_key=_scene_exit_key(requirement.archetype),
        return_key=RETURN_EXIT_KEY,
        named=True,
        caller=actor,
    )
    room.scene_archetype = requirement.archetype
    if requirement.scene_sentence:
        room.db.desc = requirement.scene_sentence
    else:
        archetype = SCENE_ARCHETYPE_REGISTRY.get(requirement.archetype)
        if archetype is not None:
            room.db.desc = archetype.scene_sentence
    return room



def _spawn_occupants(
    room: InstanceRoom,
    requirement: Any,
    objective: Any,
    quest_key: str,
) -> tuple[Any, ...]:
    """Spawn one actor per occupant role through the shared materializer.

    Every occupant is built by ``world.quests.materializer.spawn_role_actor``
    (design §5.3): the whitelisted prototype, the registry-derived traits, the
    characterization and persona card, the named portrait policy, and the
    lineage auto-seed are applied by the one shared construction path, so the
    accepted-stage and pre-acceptance encounter boundaries cannot drift.
    Monsters go through the shared whitelisted monster path. Occupants are
    registered as owned and their portrait ensures are scheduled through the
    shared helper inside the caller's atomic materialization.
    """
    occupants: list[Any] = []
    characterizations = getattr(requirement, "characterizations", ())
    for position, (role, tier_key, disposition) in enumerate(requirement.npc_reqs):
        characterization = (
            characterizations[position]
            if position < len(characterizations)
            else None
        )
        occupants.append(
            spawn_role_actor(
                room,
                RoleSpawn(
                    role=role,
                    tier=tier_key,
                    disposition=disposition,
                    characterization=characterization,
                ),
                {
                    "kind": "generated_quest",
                    "quest": quest_key,
                    "stage": requirement.index,
                    "occupant": position,
                },
            )
        )
    if objective.kind is ObjectiveKind.DEFEAT and objective.monster_tier is not None:
        for _position in range(objective.quantity):
            occupants.append(
                _spawn_monster(room, requirement.archetype, objective.monster_tier)
            )
    for occupant in occupants:
        register_owned_entity(room, occupant)
    _schedule_occupant_portraits(occupants)
    return tuple(occupants)


def _bind_stage(
    actor,
    record: Any,
    room: InstanceRoom,
    objective: Any,
    occupants: tuple[Any, ...],
) -> Any:
    living = tuple(o for o in occupants if isinstance(o, LivingEntity))
    if objective.kind is ObjectiveKind.DEFEAT:
        return bind_stage_runtime(
            actor,
            record.quest_id,
            room=room,
            objective_targets=living,
        )
    return bind_stage_runtime(actor, record.quest_id, room=room)


def _locate_anchor_room(anchor_key: str) -> AnchorRoom | None:
    for room in AnchorRoom.objects.all():
        if room.db.anchor_key == anchor_key:
            return room
    return None


def _locate_permanent(location: RoomLocator) -> Any:
    if location.kind is DestinationKind.ANCHOR:
        room = _locate_anchor_room(location.anchor_key)
        if room is None:
            raise SceneBuilderLocationError(
                f"anchor {location.anchor_key!r} has no materialized AnchorRoom"
            )
        return room
    if location.kind is DestinationKind.GRID:
        room = GridRoom.objects.filter_xyz(xyz=location.xyz).first()
        if room is None:
            raise SceneBuilderLocationError(
                f"grid room {location.xyz!r} is not materialized"
            )
        return room
    raise SceneBuilderSpawnError(
        f"unsupported permanent destination kind {location.kind.value}"
    )


def _resolve_current_requirement(record: Any, definition: Any) -> Any:
    requirements = scene_requirements_for(record.definition_key)
    if not requirements:
        raise SceneBuilderNoRequirements(
            f"quest {record.quest_id!r} stage {record.stage_index} has no "
            "registered spawn requirements"
        )
    for requirement in requirements:
        if requirement.index == record.stage_index:
            return requirement
    raise SceneBuilderNoRequirements(
        f"quest {record.quest_id!r} stage {record.stage_index} has no "
        "registered spawn requirements for its stage index"
    )


def build_flavor_context(
    requirement: Any,
    definition: Any,
    room: Any,
    origin_room: Any = None,
) -> dict[str, str] | None:
    """Assemble the bounded four-key flavor context for a freshly spawned scene.

    Returns a plain dict with exactly ``scene_sentence`` / ``quest_context`` /
    ``room_name`` / ``region`` sourced from deterministic data only: the
    requirement's scene sentence (falling back to the archetype registry's),
    the definition's display name plus quest type, the scene room's key, and
    the anchor registry's display name when the requirement declares
    ``anchor_near`` (empty otherwise). ``None`` when the scene has neither a
    requirement sentence nor a resolvable archetype sentence, so a sentence-less
    scene schedules no flavor. ``origin_room`` is accepted for call-site
    symmetry with ``materialize_stage`` and is not part of the four-key
    assembly (scene-flavor-apply D1). The helper references no generative
    module and no LLM profile, keeping the deterministic-path ban green.
    """
    sentence = requirement.scene_sentence
    if not sentence:
        archetype = SCENE_ARCHETYPE_REGISTRY.get(requirement.archetype)
        if archetype is not None:
            sentence = archetype.scene_sentence
    if not sentence:
        return None
    region = ""
    if requirement.anchor_near is not None:
        anchor = ANCHOR_REGISTRY.get(requirement.anchor_near)
        if anchor is not None:
            region = anchor.display_name_zh
    return {
        "scene_sentence": sentence,
        "quest_context": f"{definition.display_name}（{definition.quest_type.value}任務）",
        "room_name": room.key or _scene_name(requirement.archetype),
        "region": region,
    }


def apply_scene_flavor(room: Any, text: str) -> bool:
    """Apply one scene-flavor paragraph idempotently as the attribute's sole writer.

    Verifies the room's database row authoritatively before writing — a cached
    typeclass is not proof of existence after instance reclamation — and no-ops
    (``False``) when the room is gone or already carries a flavor, so a race
    between completion and a re-materialized room can never overwrite. Database
    and object-deletion exceptions are caught and also resolve to ``False``
    (logged), ``room.db.desc`` is never touched, and flavor application never
    raises (scene-flavor-apply D3).
    """
    if not isinstance(text, str) or not text.strip():
        return False
    try:
        if not ObjectDB.objects.filter(pk=room.pk).exists():
            return False
        if room.db.scene_flavor is not None:
            return False
        room.db.scene_flavor = text
        return True
    except Exception as error:  # noqa: BLE001 - bounded, never propagates (design D3)
        log_warn(
            "scene_flavor_skipped",
            context={"room": getattr(room, "pk", None)},
            exc=error,
        )
        return False



def _materialize_instance(actor, record, definition, requirement, origin_room):
    from world.quests.transitions import restore_quest_log, snapshot_quest_log

    quest_log_snapshot = snapshot_quest_log(actor)
    try:
        with transaction.atomic():
            already_bound = (
                record.stage_room_id is not None
                or bool(record.objective_target_ids)
                or bool(record.protected_entity_ids)
            )
            if already_bound:
                if record.stage_room_id is None:
                    raise SceneBuilderSpawnError(
                        f"quest {record.quest_id!r} is bound to targets but has no room"
                    )
                room = ObjectDB.objects.filter(id=record.stage_room_id).first()
                if room is None or not isinstance(room, InstanceRoom):
                    raise SceneBuilderSpawnError(
                        f"quest {record.quest_id!r} is bound to a room that no longer "
                        "exists as an InstanceRoom"
                    )
                return SceneMaterialization(room, record)

            if origin_room is None:
                raise SceneBuilderLocationError(
                    "an instance scene requires a caller origin room"
                )
            if isinstance(origin_room, InstanceRoom):
                raise SceneBuilderLocationError(
                    "cannot spawn an instance scene from inside another instance"
                )
            if requirement.anchor_near is not None:
                if getattr(origin_room, "anchor_key", None) != requirement.anchor_near:
                    raise SceneBuilderLocationError(
                        f"this scene anchors near {requirement.anchor_near!r}; "
                        "you must be at that anchor to enter"
                    )
            _revalidate_keys(requirement)

            room = _spawn_scene_room(actor, origin_room, requirement)
            objective = definition.stages[record.stage_index].objective
            occupants = _spawn_occupants(room, requirement, objective, definition.key)
            bound = _bind_stage(actor, record, room, objective, occupants)
            flavor_context = build_flavor_context(requirement, definition, room, origin_room)
            return SceneMaterialization(room, bound, flavor_context=flavor_context)
    except Exception:
        # A failure anywhere in the materialization rolls the database back,
        # but Evennia's in-process attribute cache for the actor's quest log may
        # still hold the bound value that ``bind_stage_runtime`` wrote. Restore
        # the pre-operation value so a fresh read can never observe a
        # half-materialized scene, exactly as ``transitions`` does for its own
        # surfaces.
        restore_quest_log(actor, quest_log_snapshot)
        raise


def materialize_stage(actor, quest_id: str, *, origin_room=None) -> SceneMaterialization:
    """Materialize the actor's current active stage's scene requirements.

    For an ``instance``-layer destination this spawns one ``InstanceRoom`` with
    a plain exit pair, sets the scene metadata, spawns lore-statted occupants,
    registers them as owned entities, and binds room and entity identities
    through ``bind_stage_runtime`` -- all inside one outer ``transaction.atomic()``.
    For a permanent ``anchor``/``grid`` destination it only locates the existing
    room and never spawns or binds. An already-bound current stage returns the
    existing binding and spawns nothing. Named ``SceneBuilderError`` variants
    reject unknown/inactive quests, stages without spawn requirements, and
    mismatched origins with no state change.
    """
    records = read_records(actor)
    record = find_record(records, quest_id)
    if record is None:
        raise SceneBuilderNotActive(f"unknown quest {quest_id!r}")
    if record.state is not QuestState.IN_PROGRESS:
        raise SceneBuilderNotActive(
            f"quest {quest_id!r} is not active; only an active current stage "
            "can materialize a scene"
        )
    definition = definition_for(record)
    current_stage = definition.stages[record.stage_index]
    if current_stage.index != record.stage_index:
        raise SceneBuilderNotActive(
            f"quest {record.quest_id!r} stage {record.stage_index} no longer "
            "matches its definition"
        )
    requirement = _resolve_current_requirement(record, definition)
    if requirement.location is None:
        raise SceneBuilderLocationError("the current stage declares no destination")
    if requirement.location.kind is DestinationKind.BOUND_INSTANCE:
        return _materialize_instance(actor, record, definition, requirement, origin_room)
    if requirement.location.kind in (DestinationKind.ANCHOR, DestinationKind.GRID):
        room = _locate_permanent(requirement.location)
        return SceneMaterialization(room, record)
    raise SceneBuilderSpawnError(
        f"unsupported destination kind {requirement.location.kind.value}"
    )
