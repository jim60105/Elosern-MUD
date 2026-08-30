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

from typeclasses.npcs import NPC
from world.quests.transitions import restore_quest_log, snapshot_quest_log
from world.rules.action import ActionRequest, ActionResult, ActionResolver
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import get_config
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
from world.rules.event_log import EventLog
from world.rules.surfaces import attribute_snapshot
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY


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
    ("skill_proficiency", None),
)


@dataclass(frozen=True)
class CastSettlement:
    """The committed out-of-combat cast result, its advance events, and the
    caller-facing auto-leave notification lines the settlement's coercion
    scan produced (``sexual-resist-out-of-combat``)."""

    result: ActionResult
    events: tuple[ScheduledEvent, ...]
    notifications: tuple[str, ...] = ()


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


@dataclass(frozen=True)
class _CoercionRestoreState:
    """The pre-cast party/relations surfaces of one coercion scan's forced targets.

    ``_scan_out_of_combat_sexual_coercion`` returns this so the settlement can
    restore the surfaces when a *later* step of the outer transaction fails:
    the idmapper attribute cache is not transaction-aware, so a rolled-back
    ``relations_data`` write stays readable in-process without an explicit
    restore (the scan itself restores these surfaces for failures inside its
    own penalty block). Empty for a scan that penalized nothing.
    """

    party_before: list[Any]
    members_before: dict[int, Any]
    relations_before: dict[int, Any]

    def restore(self, actor: Any) -> None:
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, self.party_before, self.members_before)
        restore_relations_surfaces(self.relations_before)


def _scan_out_of_combat_sexual_coercion(
    actor: Any, targets: list[Any], event_log: EventLog
) -> tuple[tuple[str, ...], _CoercionRestoreState | None]:
    """Apply per-forced-act coercion penalties for one resolved out-of-combat cast.

    Out-of-combat sibling of ``combat_session._scan_sexual_coercion``: scans
    the single resolved cast's ``EventLog`` for the resist-outcome contract
    ``action._step4b_sexual_resist_gate`` emits (``EventEntry(kind=
    "sexual_resist", data={"resisted": bool, "auto_comply": bool, "roll":
    int | None})``, documented in ``sexual-act-resolution-design.md`` §3.4).
    Only the actor's own log is scanned (the ``actor`` filter mirrors the
    combat scan, which must skip other combatants' own logs). Only an entry
    recording a forced outcome -- ``resisted is False`` and ``auto_comply is
    False`` -- costs the target's affinity toward the actor; a compliance
    (rolled or automatic) and a successful resistance apply no penalty. Each
    qualifying entry calls the sole affinity writer once with the
    ``sexual_forced`` source and the rulebook penalty, inside one transaction
    that also covers every resulting auto-leave -- a failure rolls the whole
    cast's affinity effects back.

    There is no ``Battlefield`` out of combat: each entry's ``target`` key
    resolves against the cast's own explicit ``targets`` list, so the correct
    scope is exactly "every ``NPC`` in the cast's target list", settled by
    construction rather than a roster decision. A target that resolves to no
    list member or to a non-``NPC`` applies no penalty (mirroring
    ``apply_affinity_change``'s own owner rejection without needing to call
    it). Returns the auto-leave notification lines and the pre-cast
    party/relations surfaces of the penalized targets (``None`` when nothing
    was penalized); the caller delivers the notifications only after the
    transaction commits (the writer never notifies) and restores the returned
    surfaces when a later settlement step fails.
    """
    player_key = str(actor.key)
    if event_log.actor != player_key:
        return (), None
    by_key = {str(target.key): target for target in targets}
    forced: list[Any] = []
    for entry in event_log.entries:
        if entry.kind != "sexual_resist":
            continue
        if not isinstance(entry.data, Mapping):
            # Fail closed on a malformed payload: never penalize, never
            # crash the cast over a bad record.
            continue
        # ``is False``, not falsy-truthiness: a missing or mistyped key
        # must read as "do not penalize" rather than accidentally matching.
        if entry.data.get("resisted") is not False:
            continue
        if entry.data.get("auto_comply") is not False:
            continue
        target = by_key.get(entry.target)
        if target is None or not isinstance(target, NPC):
            continue
        forced.append(target)
    if not forced:
        return (), None
    penalty = get_config().sexual_forced_penalty
    notifications: list[str] = []
    restore_state = _CoercionRestoreState(
        party_before=list(actor.db.party or ()),
        members_before={
            int(target.pk): target.db.party_member for target in forced
        },
        relations_before={
            int(target.pk): target.db.relations_data for target in forced
        },
    )
    try:
        with transaction.atomic():
            for target in forced:
                outcome = apply_affinity_change(
                    target, actor, AffinitySource.SEXUAL_FORCED, -penalty
                )
                if outcome.auto_leave_notification is not None:
                    notifications.append(outcome.auto_leave_notification)
    except Exception:
        # The outer settlement transaction rolled the database back; restore
        # the in-process attribute surfaces so readers never observe the
        # rolled-back values (the idmapper cache is not transaction-aware).
        restore_state.restore(actor)
        raise
    return tuple(notifications), restore_state


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
    the out-of-combat coercion scan (``_scan_out_of_combat_sexual_coercion``)
    and ``WorldClock.advance`` as nested operations inside it, and returns
    only after the outer transaction commits. A rejected resolution advances
    nothing and touches no surface. On any exception the outer rollback
    reverts the durable rows and ``_restore_settlement_state`` reconciles
    every snapshotted Evennia cache before the failure propagates.
    """
    if not isinstance(request.targets, list):
        raise ValueError(
            "settle_out_of_combat_cast requires explicit targets, got "
            f"{request.targets!r}"
        )
    act = SEXUAL_ACT_REGISTRY.get(request.skill_key)
    if act is not None and act.resistible:
        target_keys = [str(target.key) for target in request.targets]
        if len(target_keys) != len(set(target_keys)):
            # The ``sexual_resist`` entry contract is key-keyed, so a target
            # list containing two distinct entities with the same key would
            # make the coercion scan resolve every entry for that key to the
            # last list member -- double-penalizing one target and silently
            # skipping the other. Fail closed before resolution, snapshot, or
            # clock access; non-resistible casts are unaffected.
            raise ValueError(
                "settle_out_of_combat_cast requires unique entity keys in "
                f"explicit targets, got {target_keys!r}"
            )
    supplied = clock is not None
    if clock is None:
        clock = read_world_clock() or WorldClock()
    snapshot = _snapshot_settlement_state(request, clock)
    coercion_restore: _CoercionRestoreState | None = None
    try:
        with transaction.atomic():
            result = ActionResolver.resolve(request)
            if result.outcome != "success":
                return CastSettlement(result, (), ())
            notifications, coercion_restore = _scan_out_of_combat_sexual_coercion(
                request.actor, request.targets, result.event_log
            )
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
        # A failure after the scan's own penalty block (e.g. the clock
        # advance) leaves the scan's relations/party writes rolled back in
        # the database but still readable through the idmapper cache; restore
        # them explicitly so no in-process reader ever observes a value the
        # outer transaction rolled back.
        if coercion_restore is not None:
            coercion_restore.restore(request.actor)
        raise
    return CastSettlement(result, events, notifications)
