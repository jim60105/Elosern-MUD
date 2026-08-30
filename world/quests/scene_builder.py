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
from evennia.objects.models import ObjectDB
from evennia.prototypes.spawner import spawn

from typeclasses.entities import LivingEntity
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, GridRoom, InstanceRoom
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.maps.instance import register_owned_entity, spawn_instance_room
from world.quests.binding import bind_stage_runtime
from world.quests.characterization import characterize_errors, race_lifespan_upper_bound
from world.quests.compile import scene_requirements_for
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import (
    QuestState,
    definition_for,
    find_record,
    read_records,
)
from world.rules.progression import apply_lineage_auto_seed
from world.rules.traits import (
    build_initial_traits,
    trait_config_for_values,
)

SCENE_OCCUPANT_PROTOTYPE_WHITELIST: tuple[str, ...] = ("scene_npc", "scene_monster")

RETURN_EXIT_KEY = "返回"
_FALLBACK_SCENE_NAME = "任務場景"

# The deterministic adult baseline for a portrait-bearing occupant whose
# blueprint declared no ages (design D3). It is race-agnostic and always within
# the adult-to-lifespan-maximum validation range for every race (18..80 human,
# 18..1200 elf), so the art adult gate provably passes: the gate requires
# canonical integer ages, and the portrait description needs them too. A
# race-aware midpoint was rejected because it would make a default-age elf a
# thousand-year elder.
PORTRAIT_ADULT_BASELINE = 25


class SceneBuilderError(RuntimeError):
    """Base class for deterministic scene-materialization rejections."""


class SceneBuilderNotActive(SceneBuilderError):
    """The referenced quest record is unknown, inactive, or stage-mismatched."""


class SceneBuilderNoRequirements(SceneBuilderError):
    """The current stage has no registered spawn requirements (hand-written quest)."""


class SceneBuilderLocationError(SceneBuilderError):
    """The caller is not at a valid origin for the stage's destination."""


class SceneBuilderSpawnError(SceneBuilderError):
    """A scene key failed to resolve or the spawner produced an invalid object."""


@dataclass(frozen=True)
class SceneMaterialization:
    """The committed result of one stage materialization."""

    room: Any
    record: Any
    flavor_context: dict[str, str] | None = None


def _validate_occupant_parent(prototype: dict) -> None:
    """Reject any occupant prototype outside the whitelist, and reject an
    explicit ``typeclass`` override so the whitelist gates the actual spawned
    type, not merely the claimed parentage (mirrors ``world.maps.instance``)."""
    parent = prototype.get("prototype_parent")
    if parent not in SCENE_OCCUPANT_PROTOTYPE_WHITELIST:
        raise SceneBuilderSpawnError(
            f"prototype_parent {parent!r} is not in "
            "SCENE_OCCUPANT_PROTOTYPE_WHITELIST"
        )
    typeclass = prototype.get("typeclass")
    if typeclass is not None:
        raise SceneBuilderSpawnError(
            "a scene-occupant prototype must not override the typeclass; "
            "the whitelist gates the spawned type"
        )


def _scene_name(archetype_key: str | None) -> str:
    if archetype_key is None:
        return _FALLBACK_SCENE_NAME
    archetype = SCENE_ARCHETYPE_REGISTRY.get(archetype_key)
    return _FALLBACK_SCENE_NAME if archetype is None else archetype.display_name_zh


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
        _revalidate_characterization(requirement, role, tier_key, position)


def _revalidate_characterization(
    requirement: Any,
    role: str,
    tier_key: str,
    position: int,
) -> None:
    """Re-validate one occupant's characterization through the shared helper.

    The compile boundary already validated the accepted blueprint, but a
    forged ``StageSpawnRequirement`` could bypass it and write underage or
    non-integer canonical ages (a permanently adult-gated NPC) or a malformed
    policy. Re-running the same shared rules here keeps the adult invariant a
    hard floor on every spawn path: invalid data raises ``SceneBuilderSpawnError``
    and rolls the whole materialization back before any state change.
    """
    characterizations = getattr(requirement, "characterizations", ())
    if position >= len(characterizations):
        return
    characterization = characterizations[position]
    if characterization is None:
        return
    entry: dict[str, Any] = {}
    if characterization.display_name is not None:
        entry["display_name"] = characterization.display_name
    if characterization.age is not None:
        entry["age"] = characterization.age
    if characterization.apparent_age is not None:
        entry["apparent_age"] = characterization.apparent_age
    if characterization.portrait_stable_key is not None:
        entry["portrait"] = {"stable_key": characterization.portrait_stable_key}
    if characterization.background is not None:
        entry["background"] = characterization.background
    if characterization.persona:
        entry["persona"] = dict(characterization.persona)
    if not entry:
        return
    for message in characterize_errors(
        entry,
        lifespan_upper_bound=race_lifespan_upper_bound(tier_key),
    ):
        raise SceneBuilderSpawnError(
            f"invalid characterization for occupant {role!r}: {message}"
        )


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


def _apply_characterization(
    npc: NPC,
    requirement: Any,
    position: int,
) -> None:
    """Apply one compiled occupant's characterization per-field (design D1).

    Each carried field applies independently: ``display_name`` sets the display
    name; the paired ages set the canonical ``age``/``apparent_age``
    attributes; a portrait ``stable_key`` materializes the full named policy
    dict (design D2) and, when the ages are absent, the deterministic adult
    baseline ``PORTRAIT_ADULT_BASELINE`` so the art adult gate always has
    canonical inputs (design D3). An occupant without a portrait policy never
    receives the baseline or a policy (design D4). The policy is written only
    after the ages, so a policy-bearing occupant always carries canonical adult
    ages.
    """
    characterizations = getattr(requirement, "characterizations", ())
    if position >= len(characterizations):
        return
    characterization = characterizations[position]
    if characterization is None:
        return
    if characterization.display_name is not None:
        npc.db.display_name = characterization.display_name
    if characterization.age is not None and characterization.apparent_age is not None:
        npc.db.age = characterization.age
        npc.db.apparent_age = characterization.apparent_age
    if characterization.portrait_stable_key is not None:
        if npc.db.age is None:
            npc.db.age = PORTRAIT_ADULT_BASELINE
        if npc.db.apparent_age is None:
            npc.db.apparent_age = PORTRAIT_ADULT_BASELINE
        npc.db.portrait_policy = {
            "mode": "named",
            "stable_key": characterization.portrait_stable_key,
        }
    persona = dict(characterization.persona)
    if characterization.background is not None:
        persona["background"] = characterization.background
    if persona:
        # The scene-builder characterization seam is one of the two NPC-persona
        # writers (the import loader is the other); the authored flavor text
        # lands verbatim so the look appearance path renders it. The record is
        # kept in the import-card shape (empty containers for non-prose keys)
        # so every PersonaStore consumer sees the documented six-key contract.
        record = {
            "identity": {},
            "personality": persona.get("personality", ""),
            "life_story": persona.get("life_story", ""),
            "habit": persona.get("habit", ""),
            "appearance": {},
            "social_connection": {},
        }
        if characterization.background is not None:
            record["background"] = characterization.background
        npc.db.persona = record


def _spawn_npc(
    room: InstanceRoom,
    requirement: Any,
    role: str,
    tier_key: str,
    disposition: str | None,
    position: int,
) -> NPC:
    tier = NPC_TIER_REGISTRY[tier_key]
    # The tier's four bands (three physical + magic_power) drive the whole
    # stat block; the deleted race-level magic fields have no caller (D-A2).
    config = trait_config_for_values(
        build_initial_traits(tier.race_key, tier=tier.static_tier_key)
    )

    prototype = {
        "prototype_parent": "scene_npc",
        "key": f"{_scene_name(requirement.archetype)}的{role}",
        "location": room,
    }
    _validate_occupant_parent(prototype)
    spawned = spawn(prototype)
    if not spawned:
        raise SceneBuilderSpawnError(
            "spawner.spawn() returned no object for a scene NPC"
        )
    npc = spawned[0]
    if not isinstance(npc, NPC):
        raise SceneBuilderSpawnError(
            f"spawned object {npc!r} is not an NPC; rejecting it"
        )
    npc.race = tier.race_key
    npc._apply_trait_config(config)
    npc.db.disposition = disposition
    _apply_characterization(npc, requirement, position)
    # The shared lineage auto-seed (use-driven-skill-lineage DC6): a spawned
    # NPC that owns a deep skill gets its prerequisite chain closed and each
    # unsatisfied edge seeded to exactly the required proficiency, so its
    # skills are usable on spawn. No-op for a skill-less prototype.
    apply_lineage_auto_seed(npc)
    return npc


def _spawn_monster(
    room: InstanceRoom,
    requirement: Any,
    tier_key: str,
    position: int,
) -> Monster:
    prototype = {
        "prototype_parent": "scene_monster",
        "key": f"{_scene_name(requirement.archetype)}的魔物",
        "location": room,
    }
    _validate_occupant_parent(prototype)
    spawned = spawn(prototype)
    if not spawned:
        raise SceneBuilderSpawnError(
            "spawner.spawn() returned no object for a scene monster"
        )
    monster = spawned[0]
    if not isinstance(monster, Monster):
        raise SceneBuilderSpawnError(
            f"spawned object {monster!r} is not a Monster; rejecting it"
        )
    monster.threat_tier = tier_key
    monster.apply_monster_tier("floor")
    return monster


def _spawn_occupants(
    room: InstanceRoom,
    requirement: Any,
    objective: Any,
) -> tuple[Any, ...]:
    occupants: list[Any] = []
    for position, (role, tier_key, disposition) in enumerate(requirement.npc_reqs):
        occupants.append(
            _spawn_npc(room, requirement, role, tier_key, disposition, position)
        )
    if objective.kind is ObjectiveKind.DEFEAT and objective.monster_tier is not None:
        for position in range(objective.quantity):
            occupants.append(
                _spawn_monster(room, requirement, objective.monster_tier, position)
            )
    for occupant in occupants:
        register_owned_entity(room, occupant)
    _schedule_occupant_portraits(occupants)
    return tuple(occupants)


def _schedule_occupant_portraits(occupants: tuple[Any, ...] | list[Any]) -> None:
    """Schedule the portrait ensure for occupants carrying an explicit named policy.

    Runs inside the outer atomic materialization, so ``transaction.on_commit``
    fires only after the spawn transaction commits and an art failure can never
    roll back a materialized scene (design D9). Today's role-based occupants
    carry no policy and schedule nothing.
    """
    named = [
        occupant
        for occupant in occupants
        if getattr(occupant, "db", None) is not None
        and occupant.db.portrait_policy is not None
        and hasattr(occupant.db.portrait_policy, "get")
        and occupant.db.portrait_policy.get("mode") == "named"
    ]
    if not named:
        return
    from world.art.service import schedule_occupant_portrait

    for occupant in named:
        schedule_occupant_portrait(occupant)


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
    except Exception:  # noqa: BLE001 - bounded, never propagates (design D3)
        from evennia import logger

        logger.log_warn(f"scene flavor apply skipped: room {getattr(room, 'pk', None)}")
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
            occupants = _spawn_occupants(room, requirement, objective)
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
