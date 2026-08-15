"""Outer settlement boundary for out-of-combat skill casts.

``CmdCast._cast_out_of_combat`` routes every out-of-combat cast through
``settle_out_of_combat_cast``: the skill effect, practice award, planner
writes, and the command-time charge commit together inside one outer
``transaction.atomic()``. On any failure the outer rollback reverts the durable
rows and the settlement restores every snapshotted Evennia cache -- actor and
target attributes, the battlefield's fled/knocked-out sets, every
callback-owned advance surface, and the clock tick -- to the pre-action state
before the failure propagates (security-audit run-3 finding index 6).
"""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from django.db import transaction
from evennia.utils.logger import log_warn

from world.quests.transitions import restore_quest_log, snapshot_quest_log
from world.rules.action import ActionRequest, ActionResult, ActionResolver
from world.rules.clock import (
    MAX_ADVANCE_SECONDS,
    AdvanceSource,
    ScheduledEvent,
    WorldClock,
    _flush_deleted_instance,
    _refresh_advance_entity_caches,
    _restore_advance_location,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
    read_world_clock,
)
from world.rules.surfaces import attribute_snapshot


# The action- and clock-touched attribute surfaces of one actor or target: the
# ``_ADVANCE_ENTITY_SURFACES`` declaration minus the sexual-decay accumulators,
# which only ``advance()`` ever writes on its own caller entities (the actor)
# and which the registry's actor entry already covers through the seam. The
# climax-settlement bookkeeping attributes are included: an action may stage
# or consume them on any target, so the outer rollback must restore them.
_ENTITY_SURFACES: tuple[tuple[str, str | None], ...] = (
    ("traits", "traits"),
    ("disguised_stats", None),
    ("sexual_traits", "traits"),
    ("virgin", "sexual_state"),
    ("experience_types", "sexual_state"),
    ("climax_turns", "sexual_state"),
    ("pending_climax_extension", "sexual_state"),
    ("buffs", None),
    ("skill_grants", None),
    ("magic_xp", None),
    ("skill_proficiency", None),
)


@dataclass(frozen=True)
class CastSettlement:
    """The committed out-of-combat cast result and its advance events."""

    result: ActionResult
    events: tuple[ScheduledEvent, ...]


@dataclass
class _SettlementObjectSnapshot:
    """One object's pre-action state in the settlement superset.

    ``attributes`` maps ``(key, category)`` to ``(existed, value)`` exactly as
    the shared ``attribute_snapshot`` helper returns. ``location`` is the
    sibling seam's ``(existed, pre-advance db_location pk)``; ``battlefield``
    holds the fled/knocked-out sets for a battlefield-shaped object;
    ``refresh_caches`` marks the caller-scope entities whose trait/sexual
    caches are reloaded after restore.
    """

    obj: Any
    attributes: dict[tuple[str, str | None], tuple[bool, Any]]
    location: tuple[bool, int] | None = None
    battlefield: tuple[frozenset[Any], frozenset[Any]] | None = None
    refresh_caches: bool = False


@dataclass
class _SettlementSnapshot:
    """The merged pre-resolution superset plus the pre-action clock tick."""

    objects: dict[int, _SettlementObjectSnapshot]
    tick: tuple[int, tuple[bool, Any] | None]


def _entity_attributes(
    entity: Any,
) -> dict[tuple[str, str | None], tuple[bool, Any]]:
    """Snapshot one entity's action surfaces plus its quest log."""
    attributes = {
        (key, category): attribute_snapshot(entity, key, category)
        for key, category in _ENTITY_SURFACES
    }
    attributes[("quest_log", None)] = snapshot_quest_log(entity)
    return attributes


def _merged_object(
    objects: dict[int, _SettlementObjectSnapshot],
    obj: Any,
    attributes: Mapping[tuple[str, str | None], tuple[bool, Any]],
) -> None:
    """Merge one object's attribute surfaces into the identity-keyed mapping."""
    entry = objects.get(id(obj))
    if entry is None:
        objects[id(obj)] = _SettlementObjectSnapshot(
            obj=obj, attributes=dict(attributes)
        )
    else:
        entry.attributes.update(attributes)


def _snapshot_settlement_state(
    request: ActionRequest, clock: WorldClock
) -> _SettlementSnapshot:
    """Build the pre-resolution snapshot superset, merged by object identity.

    Runs entirely before the outer transaction opens. The merged advance
    registry (``fix-clock-rollback-cache-sync`` D6 seam) covers the actor's
    advance surfaces and every callback-owned surface; the actor's and every
    request target's entity surfaces plus quest log, and the battlefield's
    fled/knocked-out sets when the request context carries one, are merged into
    the same identity-keyed mapping; the clock tick closes the superset. A
    contract that raises here fails the settlement before the transaction opens
    and before any write (fail-closed, exactly the sibling's D2 mandate).
    """
    registry = build_advance_snapshot_registry(
        clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (request.actor,)
    )
    cached = {
        id(obj): obj for obj in _cached_db_instances()
    }
    objects: dict[int, _SettlementObjectSnapshot] = {}
    for obj_id, snapshot in registry.items():
        obj = cached.get(obj_id)
        if obj is None:
            continue
        objects[obj_id] = _SettlementObjectSnapshot(
            obj=obj,
            attributes=dict(snapshot.attributes),
            location=snapshot.location,
        )
    caller_entities = (request.actor, *request.targets)
    for entity in caller_entities:
        _merged_object(objects, entity, _entity_attributes(entity))
        objects[id(entity)].refresh_caches = True
    battlefield = getattr(request.context, "battlefield", None)
    if battlefield is not None:
        entry = objects.get(id(battlefield))
        fled = frozenset(battlefield.fled)
        knocked_out = frozenset(getattr(battlefield, "knocked_out", ()))
        if entry is None:
            objects[id(battlefield)] = _SettlementObjectSnapshot(
                obj=battlefield,
                attributes={},
                battlefield=(fled, knocked_out),
            )
        else:
            entry.battlefield = (fled, knocked_out)
    return _SettlementSnapshot(objects=objects, tick=_snapshot_clock_tick(clock))


def _cached_db_instances() -> Iterable[Any]:
    """Every object instance currently held by the shared idmapper cache.

    The registry's discovery queries populate this cache before the snapshot
    resolves contract-discovered objects into the settlement entries, so
    restore never needs to re-query: the very instances the contract touched
    are the ones restored, exactly like the sibling's restore step.
    """
    from evennia.objects.models import ObjectDB

    return ObjectDB.get_all_cached_instances()


def _restore_attribute_direct(
    obj: Any,
    key: str,
    category: str | None,
    snapshot: tuple[bool, Any],
) -> None:
    """Restore one attribute surface, degrading to a cache reset on failure.

    Writes the snapshot value directly instead of through the shared
    ``restore_attribute`` deepcopy: a registry surface may embed live database
    objects (the instance contract's ``owned_entities``), which plain
    ``deepcopy`` cannot copy; Evennia's ``attributes.add`` re-encodes through
    ``dbserialize`` and handles them natively. Mirrors the sibling's registry
    restore so a regular rollback never depends on cache invalidation.
    """
    existed, value = snapshot
    try:
        if existed:
            obj.attributes.add(key, value, category=category)
        else:
            obj.attributes.remove(key, category=category)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:
            pass
        log_warn(f"cast settlement could not restore {key!r} on {obj}: {error}")


def _restore_settlement_state(
    snapshot: _SettlementSnapshot, clock: WorldClock
) -> None:
    """Restore every snapshotted surface after the outer rollback.

    Runs in fixed deterministic order, best-effort per step with a logged
    diagnostic on failure (a failing step degrades to the next and never masks
    the original exception): first the clock tick from its pre-action snapshot,
    then every object's attribute/location/battlefield surfaces, then the
    caller-scope entities' trait/sexual cache refresh. Registry entries with a
    recorded location re-fetch the pre-action room by its stored primary key
    and assign it through the location setter so Evennia's contents caches are
    reconciled, exactly per the sibling's D3.
    """
    _restore_clock_tick(clock, snapshot.tick)
    for entry in snapshot.objects.values():
        obj = entry.obj
        if getattr(obj, "_is_deleted", False):
            _flush_deleted_instance(obj)
            continue
        for (key, category), surface in entry.attributes.items():
            if key == "quest_log":
                restore_quest_log(obj, surface)
            else:
                _restore_attribute_direct(obj, key, category, surface)
        if entry.location is not None:
            existed, target_pk = entry.location
            try:
                if existed:
                    _restore_advance_location(obj, target_pk)
                else:
                    obj.location = None
            except Exception as error:
                log_warn(
                    f"cast settlement could not restore the location of {obj}: {error}"
                )
        if entry.battlefield is not None:
            try:
                fled, knocked_out = entry.battlefield
                obj.fled = set(fled)
                if hasattr(obj, "knocked_out"):
                    obj.knocked_out = set(knocked_out)
            except Exception as error:
                log_warn(
                    f"cast settlement could not restore the battlefield {obj}: {error}"
                )
    for entry in snapshot.objects.values():
        if entry.refresh_caches:
            _refresh_advance_entity_caches(entry.obj)


def settle_out_of_combat_cast(
    request: ActionRequest, *, clock: WorldClock | None = None
) -> CastSettlement:
    """Resolve one out-of-combat cast and its command-time charge atomically.

    Accepts only explicit target lists: the ``"all-enemies"`` / ``"all-allies"``
    / ``"all"`` shorthands belong to the combat-session path and are rejected
    here with ``ValueError`` before any clock access, because the snapshot
    superset is defined over concrete targets. The world-clock singleton is
    never created by this entry: a missing singleton is read without creation
    (``read_world_clock``) for the pre-resolution snapshot, and the real
    singleton is obtained only after resolution succeeds, so a rejected cast
    touches no surface and persists nothing.

    Snapshots every action- and clock-touched surface before opening the outer
    transaction, runs ``ActionResolver.resolve`` and -- only on success --
    ``WorldClock.advance`` as nested operations inside it, and returns only
    after the outer transaction commits. A rejected resolution advances nothing
    and touches no surface. On any exception the outer rollback reverts the
    durable rows and ``_restore_settlement_state`` reconciles every snapshotted
    Evennia cache before the failure propagates.
    """
    if not isinstance(request.targets, list):
        raise ValueError(
            "settle_out_of_combat_cast requires explicit targets, got "
            f"{request.targets!r}"
        )
    supplied = clock is not None
    if clock is None:
        clock = read_world_clock() or WorldClock()
    snapshot = _snapshot_settlement_state(request, clock)
    try:
        with transaction.atomic():
            result = ActionResolver.resolve(request)
            if result.outcome != "success":
                return CastSettlement(result, ())
            if not supplied and getattr(clock, "_script", None) is None:
                clock = get_world_clock()
            events = tuple(
                clock.advance(
                    result.time_cost_seconds,
                    AdvanceSource.COMMAND,
                    (request.actor,),
                )
            )
    except Exception:
        _restore_settlement_state(snapshot, clock)
        raise
    return CastSettlement(result, events)
