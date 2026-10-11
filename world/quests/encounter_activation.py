"""Pre-acceptance encounter activation: the durable scene lifecycle boundary.

``activate_scene_encounter`` gives one published encounter, for one player, one
durable activation identity and one exact set of role bindings -- without
accepting a quest, fabricating an active ``QuestRecord``, or revealing a future
secret. Unaccepted remains represented by absence from the player's accepted
quest log (design §3/§5.2).

The boundary is deterministic and owns its transaction:

1. resolve the published package and revalidate the whole package;
2. derive the declared prerequisites from committed package state (a caller
   supplied observation mapping is only verified against that view, never
   trusted), resolve the encounter locator through the existing map authority,
   and check the availability of every already-bound role actor;
3. reserve the ``(package, scene, player)`` identity under its database
   uniqueness constraint before any materialization;
4. in one transaction, reuse the exact bound actors or spawn only the encounter's
   required unbound roles through the shared materializer, provision the declared
   scoped issuer and register its commission, bind roles, write initial role
   knowledge through the narrative owner, initialize the selected phase, and
   commit the activation identity;
5. schedule the portrait ensures only after the commit.

A named unavailable outcome (wrong locator, unmet prerequisite, missing, dead or
departed actor, cancelled encounter, issuer-key collision) writes no activation,
binding, commission or quest state and leaves the scene invocable under the same
identity; it may record the actor's current availability on the role binding as a
diagnostic (``lookup_story_role`` reports it) but never the activation itself. A
technical failure rolls the transaction back, evicts the Evennia caches of
anything it created, and leaves the same identity invocable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.utils.idmapper.models import flush_cache

from world.observability import log_info, log_warn
from world.rules.quest_issuance import Settlement

from . import scene_store
from .binding import _is_living
from .compile import publish_activated_commission
from .definitions import DestinationKind
from .encounters import ScenePackageNotFound
from .materializer import RoleSpawn, schedule_occupant_portraits, spawn_role_actor
from .phases import condition_matches, resolve_observations
from .scene_package import ScenePackageDefinition, validate_scene_package

STATE_UNAVAILABLE = "unavailable"


class SceneEncounterNotFound(LookupError):
    """The referenced encounter is not declared by the package."""


class EncounterUnavailable(RuntimeError):
    """Activation refused for a named reason, with no state written."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason
        self.message = message or reason


@dataclass(frozen=True)
class EncounterActivation:
    """The committed result of one encounter activation attempt."""

    package_id: str
    scene_id: str
    state: str
    reason: str
    created: bool
    role_bindings: dict[str, int] = field(default_factory=dict)
    commission_keys: tuple[str, ...] = ()
    room_id: int | None = None

    @property
    def activated(self) -> bool:
        return self.state == scene_store.ENCOUNTER_ACTIVATED


def committed_observations(package_id: str) -> dict[str, bool]:
    """Derive the registered observations from committed package runtime state.

    The facts are read from committed phase selections, never from prose and
    never from caller text: ``closure`` holds when a role's selected phase is its
    declared closure phase and ``abandoned`` when an unresolved terminal phase was
    selected; ``separation``/``unresolved`` describe the story state before any
    closure. Guarded escort/reunion observations are never derived here.
    """
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    definition = validate_scene_package(row.payload)
    facts = {
        "separation": True,
        "unresolved": True,
        "closure": False,
        "abandoned": False,
    }
    for role_dialogue in definition.dialogue:
        runtime = scene_store.get_dialogue_phase(package_id, role_dialogue.role_id)
        if runtime is None:
            continue
        phase = next(
            (
                item
                for item in role_dialogue.phases
                if item.phase_id == runtime.selected_phase
            ),
            None,
        )
        if phase is None:
            continue
        for condition in phase.conditions:
            if condition.get("default"):
                continue
            fact, expected = next(iter(condition.items()))
            if fact in facts and expected is True:
                facts[fact] = True
    if facts["closure"]:
        facts["unresolved"] = False
    if facts["abandoned"]:
        facts["separation"] = False
    return facts


def _unavailable(
    package_id: str, scene_id: str, player: Any, reason: str, *, tick: int
) -> EncounterActivation:
    log_warn(
        "scene_encounter_unavailable",
        context={
            "package": package_id,
            "scene": scene_id,
            "char": str(getattr(player, "pk", "?")),
            "reason": reason,
            "tick": str(tick),
        },
    )
    return EncounterActivation(
        package_id=package_id,
        scene_id=scene_id,
        state=STATE_UNAVAILABLE,
        reason=reason,
        created=False,
    )


def _locate_permanent(locator: Any) -> tuple[Any | None, str]:
    """Resolve a permanent encounter destination through the existing map authority."""
    from typeclasses.rooms import AnchorRoom, GridRoom

    if locator.kind is DestinationKind.ANCHOR:
        for room in AnchorRoom.objects.all():
            if room.db.anchor_key == locator.anchor_key:
                return room, ""
        return None, "locator_unavailable"
    if locator.kind is DestinationKind.GRID:
        room = GridRoom.objects.filter_xyz(xyz=locator.xyz).first()
        return (room, "") if room is not None else (None, "locator_unavailable")
    return None, "locator_unavailable"


def _resolve_instance_room(
    row: Any, encounter_row: Any, encounter: Any, origin_room: Any
) -> tuple[Any | None, str]:
    """Return the one instance room of an instance-layer encounter, creating it once."""
    if encounter_row.room_id is not None:
        room = ObjectDB.objects.filter(id=int(encounter_row.room_id)).first()
        if room is None:
            return None, "locator_unavailable"
        return room, ""
    if origin_room is None:
        return None, "locator_unavailable"
    from world.maps.instance import spawn_instance_room

    key = encounter.archetype or "任務場景"
    room = spawn_instance_room(
        origin_room,
        {"prototype_parent": "instance_room", "key": key},
        exit_key=key,
        return_key="返回",
        named=True,
        caller=None,
    )
    scene_store.set_encounter_room(
        row, encounter.scene_id, encounter_row.player_id, int(room.pk)
    )
    return room, ""


def _resolve_actor(npc_id: int) -> tuple[Any | None, str]:
    """Return ``(actor, reason)`` for one bound actor identity without repair."""
    from typeclasses.npcs import NPC

    obj = ObjectDB.objects.filter(id=int(npc_id)).first()
    if obj is None or not isinstance(obj, NPC):
        return None, "actor_missing"
    if not _is_living(obj):
        return None, "actor_dead"
    if obj.location is None:
        return None, "actor_departed"
    return obj, ""


def _grant_role_knowledge(
    actor: Any,
    definition: ScenePackageDefinition,
    role_id: str,
    package_id: str,
    *,
    tick: int,
) -> None:
    """Write one role's own permitted knowledge through the narrative owner.

    Only the role's own provenance-bearing claims are recorded; a relationship or
    another role's claim grants nothing. The stable source identity makes a
    repeat activation idempotent.
    """
    from world.narrative.memory import record_memory

    for claim in definition.knowledge:
        if claim.role_id != role_id:
            continue
        record_memory(
            owner_id=str(actor.pk),
            content={
                "claim_id": claim.claim_id,
                "claim": claim.text,
                "package": package_id,
                "role": role_id,
            },
            tick=tick,
            category="knowledge",
            knowledge_scope="witnessed",
            source_id=f"scene:{package_id}:{role_id}:{claim.claim_id}",
            projector_version=1,
        )


def _provision_role(
    definition: ScenePackageDefinition,
    role_id: str,
    row: Any,
    actor: Any,
    *,
    tick: int,
) -> str | None:
    """Provision the declared scoped commission for one freshly spawned issuer."""
    commission = definition.commission
    if commission is None or commission.role_id != role_id:
        return None
    from world.rules.quest_issuance import provision_scoped_issuer

    payload_commission = row.payload.get("commission")
    content_key = (
        payload_commission.get("issuer_content_key")
        if isinstance(payload_commission, dict)
        else None
    )
    actual = provision_scoped_issuer(actor, content_key=content_key)
    scene_store.assign_grant_actor(
        row, role_id, commission.definition_key, int(actor.pk), tick=tick
    )
    publish_activated_commission(
        commission.definition_key, actual, definition.quest.reward, Settlement.AUTO
    )
    scene_store.set_grant_registered(
        row, role_id, commission.definition_key, True, tick=tick
    )
    return actual


def ensure_package_role(
    row: Any,
    definition: ScenePackageDefinition,
    role_id: str,
    room: Any,
    *,
    provenance: dict[str, Any],
    created_pks: list[int] | None = None,
    tick: int = 0,
) -> tuple[Any, str | None]:
    """Return the exact actor bound to one package role, materializing it if unbound.

    Shared by the pre-acceptance activation boundary and the accepted-stage
    permanent-destination path (design §5.3), so the two cannot drift. A role
    with a committed binding keeps its exact actor at its actual location --
    never teleported, re-created, or re-configured -- and a missing, dead or
    departed actor raises ``EncounterUnavailable`` with its named reason instead
    of producing a replacement. Only an unbound role is spawned through the
    shared materializer, bound, given its initial phase, granted its own
    permitted knowledge and -- when it owns the package commission -- provisioned
    and registered. Historical knowledge is append-only, so a repeat entry is
    idempotent. Returns ``(actor, commission_key_or_None)``.
    """
    binding = scene_store.get_role_binding(row.package_id, role_id)
    if binding is not None:
        actor, reason = _resolve_actor(binding.npc_id)
        if actor is None:
            raise EncounterUnavailable(reason)
    else:
        role = definition.role(role_id)
        if role is None:
            raise EncounterUnavailable("unknown_role")
        role_dialogue = definition.role_dialogue(role_id)
        actor = spawn_role_actor(
            room,
            RoleSpawn(
                role=role_id,
                tier=role.tier,
                disposition=role.disposition,
                characterization=role.characterization,
                conversable=role.conversable,
                dialogue_key=(
                    f"scene_role:{row.package_id}:{role_id}"
                    if role.conversable
                    else None
                ),
            ),
            provenance,
        )
        if created_pks is not None:
            created_pks.append(int(actor.pk))
        scene_store.bind_role(
            row, role_id, int(actor.pk), provenance=provenance, tick=tick
        )
        scene_store.set_role_availability(row.package_id, role_id, "bound", tick=tick)
        if role_dialogue is not None:
            scene_store.set_dialogue_phase(
                row, role_id, role_dialogue.initial_phase, tick=tick
            )
    _grant_role_knowledge(actor, definition, role_id, row.package_id, tick=tick)
    key = _provision_role(definition, role_id, row, actor, tick=tick)
    return actor, key


def _replay(
    row: Any,
    encounter: Any,
    existing: Any,
    definition: ScenePackageDefinition,
) -> EncounterActivation:
    """Return the committed activation state without creating anything."""
    bindings = {
        binding.role_id: binding.npc_id
        for binding in scene_store.list_role_bindings(row.package_id)
        if binding.role_id in encounter.role_ids
    }
    return EncounterActivation(
        package_id=row.package_id,
        scene_id=encounter.scene_id,
        state=scene_store.ENCOUNTER_ACTIVATED,
        reason="",
        created=False,
        role_bindings=bindings,
        commission_keys=tuple(
            grant.issuer_key
            for grant in scene_store.list_commission_grants(row.package_id)
            if grant.registered
            and definition.commission is not None
            and grant.role_id == definition.commission.role_id
        ),
        room_id=existing.room_id,
    )


def activate_scene_encounter(
    player: Any,
    package_id: str,
    scene_id: str,
    *,
    room: Any = None,
    tick: int = 0,
    observations: dict[str, bool] | None = None,
) -> EncounterActivation:
    """Activate one published encounter for one player, or name why it cannot.

    ``room`` is the actual room the activation happened in: for a permanent
    encounter it must be the located room; for an instance-layer encounter it is
    the origin room the instance is reached from. ``observations`` may be supplied
    by an owner-aware caller, but it is only verified against the committed view
    from :func:`committed_observations`: a fabricated mapping can never select a
    different outcome.
    """
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    if row.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        return _unavailable(package_id, scene_id, player, "package_cancelled", tick=tick)
    definition = validate_scene_package(row.payload)
    encounter = definition.encounter(scene_id)
    if encounter is None:
        raise SceneEncounterNotFound(
            f"scene {scene_id!r} is not declared by package {package_id!r}"
        )

    existing = scene_store.get_encounter(package_id, scene_id, int(player.pk))
    if existing is not None and existing.state == scene_store.ENCOUNTER_CANCELLED:
        return _unavailable(package_id, scene_id, player, "cancelled", tick=tick)

    # Every entry -- first activation, repeat entry, reconnect and restart --
    # revalidates the exact bound actors before returning or committing anything:
    # a missing, dead or departed actor is a named unavailable outcome and never
    # a replacement actor (design §5.2). A bound actor is never teleported back.
    bound: dict[str, Any] = {}
    for role_id in encounter.role_ids:
        binding = scene_store.get_role_binding(package_id, role_id)
        if binding is None:
            continue
        actor, actor_reason = _resolve_actor(binding.npc_id)
        if actor is None:
            scene_store.set_role_availability(package_id, role_id, actor_reason, tick=tick)
            return _unavailable(package_id, scene_id, player, actor_reason, tick=tick)
        bound[role_id] = actor
    if existing is not None and existing.state == scene_store.ENCOUNTER_ACTIVATED:
        return _replay(row, encounter, existing, definition)

    committed = committed_observations(package_id)
    for fact, value in resolve_observations(observations).items():
        if committed.get(fact, False) is not value:
            raise EncounterUnavailable(
                "observation_mismatch",
                f"observation {fact!r} contradicts the committed scene state",
            )
    for condition in encounter.prerequisites:
        if not condition_matches(condition, committed):
            return _unavailable(
                package_id, scene_id, player, "prerequisite_unmet", tick=tick
            )

    locator = encounter.locator
    located = None
    if locator.kind in (DestinationKind.ANCHOR, DestinationKind.GRID):
        located, reason = _locate_permanent(locator)
        if located is None:
            return _unavailable(package_id, scene_id, player, reason, tick=tick)
        if room is not None and int(room.pk) != int(located.pk):
            return _unavailable(package_id, scene_id, player, "wrong_locator", tick=tick)

    created_pks: list[int] = []
    bindings: dict[str, int] = {}
    commission_keys: list[str] = []
    try:
        with transaction.atomic():
            encounter_row, _reserved = scene_store.reserved_encounter(
                row, scene_id, int(player.pk), tick=tick
            )
            if encounter_row.state == scene_store.ENCOUNTER_CANCELLED:
                raise EncounterUnavailable("cancelled")
            if locator.kind is DestinationKind.BOUND_INSTANCE:
                located, reason = _resolve_instance_room(
                    row, encounter_row, encounter, room
                )
                if located is None:
                    raise EncounterUnavailable(reason)
            for role_id in encounter.role_ids:
                # One shared path for both boundaries: a bound role keeps its
                # exact actor where it is, an unbound role is materialized once.
                actor, key = ensure_package_role(
                    row,
                    definition,
                    role_id,
                    located,
                    provenance={
                        "kind": "scene_encounter",
                        "package": package_id,
                        "scene": scene_id,
                        "role": role_id,
                    },
                    created_pks=created_pks,
                    tick=tick,
                )
                if key is not None:
                    commission_keys.append(key)
                bindings[role_id] = int(actor.pk)
            scene_store.mark_encounter_activated(
                row, scene_id, int(player.pk), activation_tick=tick, tick=tick
            )
    except EncounterUnavailable as error:  # observability: ignore R2: the named unavailability is emitted as scene_encounter_unavailable by _unavailable() and returned to the caller
        evict_created_actors(created_pks)
        return _unavailable(package_id, scene_id, player, error.reason, tick=tick)
    except Exception:
        evict_created_actors(created_pks)
        raise

    actors = [
        actor
        for actor in (ObjectDB.objects.filter(id=pk).first() for pk in bindings.values())
        if actor is not None
    ]
    if actors:
        transaction.on_commit(lambda present=actors: schedule_occupant_portraits(present))
    log_info(
        "scene_encounter_activated",
        context={
            "package": package_id,
            "scene": scene_id,
            "char": str(player.pk),
            "room": str(getattr(located, "pk", "")),
            "tick": str(tick),
            "roles": ",".join(sorted(bindings)),
        },
    )
    return EncounterActivation(
        package_id=package_id,
        scene_id=scene_id,
        state=scene_store.ENCOUNTER_ACTIVATED,
        reason="",
        created=True,
        role_bindings=bindings,
        commission_keys=tuple(commission_keys),
        room_id=int(located.pk) if located is not None else None,
    )


def cancel_scene_encounter(
    player: Any, package_id: str, scene_id: str, *, tick: int = 0
) -> bool:
    """Cancel one player's encounter so it can never activate afterwards."""
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    encounter_row, _created = scene_store.reserved_encounter(
        row, scene_id, int(player.pk), tick=tick
    )
    if encounter_row.state in (
        scene_store.ENCOUNTER_ACTIVATED,
        scene_store.ENCOUNTER_CANCELLED,
    ):
        return False
    scene_store.set_encounter_state(
        row, scene_id, int(player.pk), scene_store.ENCOUNTER_CANCELLED, tick=tick
    )
    log_info(
        "scene_encounter_cancelled",
        context={
            "package": package_id,
            "scene": scene_id,
            "char": str(player.pk),
            "tick": str(tick),
        },
    )
    return True


def evict_created_actors(created_pks: list[int]) -> None:
    """Evict the Evennia caches of actors a rolled-back activation created.

    Django rolls the rows back; the idmapper would otherwise keep a cached
    instance for a primary key whose row no longer exists, so a later read could
    observe a phantom actor. Shared by every caller that materializes package
    roles inside a transaction.
    """
    if created_pks:
        flush_cache()


__all__ = [
    "EncounterActivation",
    "EncounterUnavailable",
    "SceneEncounterNotFound",
    "activate_scene_encounter",
    "cancel_scene_encounter",
    "committed_observations",
    "ensure_package_role",
    "evict_created_actors",
]
