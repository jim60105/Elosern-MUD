"""Deterministic all-or-nothing movement settlement (movement-settlement-atomicity).

Evennia persists a successful location change before ``Exit.at_post_traverse``
runs, so a failing post-traverse step used to leave the player relocated with
world time, map knowledge, and companions behind (security-audit run-3 finding
index 2). ``settle_movement`` is the single outer boundary every project exit
lineage opens in ``at_traverse``: one database transaction covers the Evennia
relocation, the clock charge (``charge_movement``), the destination
map-knowledge recording (``record_arrival``), and companion following
(``follow_companions``) as one all-or-nothing unit. On any failure — an
exception inside the transaction, an outer-commit failure, or a falsy
wilderness-lineage return that relocated the traverser anyway — the already
persisted relocation is compensated in a fixed deterministic order before the
failure surfaces: traverser and companions are moved back, the wilderness
script's bookkeeping is restored from shallow snapshots, and every Evennia
in-process cache surface the settlement touched is reconciled. Django rollback
alone reverts only durable rows; the idmapper's ``db_location``, the rooms'
``contents_cache``, and the per-object attribute backend cache keep the
post-write values, so compensation must restore them explicitly.

The boundary consumes the clock advance-surface seam settled by the parallel
``fix-clock-rollback-cache-sync`` change: ``build_advance_snapshot_registry``
plus the clock-tick snapshot/restore and the canonical registry restore
(``_restore_advance_registry``), so callback-owned surfaces (quest logs and
room pins, merchant stock, NPC schedule state and location, instance state,
pruned map knowledge) are covered whichever transaction boundary fails. The
registry is built before the outer transaction opens, exactly as that change's
D6 mandates for outer-owner consumers. Residual: for a player traverser the
pre-transaction snapshot reads the world clock through ``get_world_clock()``,
which may materialize the idempotent clock-singleton Script when no advance has
ever run; production always has the singleton after the first charged action,
and the script is the canonical registry singleton, so this is accepted and
documented (design D2).
"""

from dataclasses import dataclass
from typing import Any, Callable

from django.db import transaction
from evennia.utils.search import search_script

from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_warn
from world.quests.transitions import snapshot_pin_reasons, snapshot_quest_log
from world.rules.clock import (
    AdvanceSource,
    MAX_ADVANCE_SECONDS,
    SurfaceSnapshot,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
)
from world.rules.party import _companion_co_located, live_companions
from world.rules.surfaces import attribute_snapshot

# Move-observable attribute surfaces the settlement can write on the
# traverser, snapshotted directly (the advance registry covers the remainder).
# ``quest_log`` and the destination room's pin/state surfaces use the quest
# module's own helpers so the two writers never drift.
_TRAVERSER_SURFACES: tuple[str, ...] = ("map_knowledge",)


@dataclass
class CompanionState:
    """One co-located companion's pre-move location and wilderness registration.

    ``registration`` is the script's ``itemcoordinates`` entry (a coordinate
    tuple) when the companion was tracked in the wilderness, else ``None``.
    """

    npc: Any
    location: Any
    registration: tuple[int, int] | None


@dataclass
class MovementSnapshot:
    """Pre-move state the settlement boundary needs to compensate a failure.

    The wilderness bookkeeping snapshots are shallow copies (shared object
    references, never ``deepcopy``: the dicts are keyed by live Evennia
    objects, which the shared restore helper's ``deepcopy`` cannot copy).
    ``wilderness_coordinates``/``wilderness_source_coordinates`` mirror the
    ``settle_movement`` call, so compensation can tell a gate entry from a
    wilderness step or grid return. ``registry`` and the clock fields are
    ``None`` for non-``PlayerCharacter`` traversers, whose settlement steps are
    internal no-ops.
    """

    traverser: Any
    source_location: Any
    wilderness: Any
    wilderness_coordinates: tuple[int, int] | None
    wilderness_source_coordinates: tuple[int, int] | None
    traverser_registration: tuple[int, int] | None
    companions: list[CompanionState]
    wilderness_itemcoordinates: dict | None
    wilderness_rooms: dict | None
    wilderness_unused_rooms: list | None
    registry: dict[int, SurfaceSnapshot] | None
    clock: Any
    tick_snapshot: Any


def settle_movement(
    traversing_object: Any,
    source_location: Any,
    *,
    traverse: Callable[[], Any],
    destination: Any | None = None,
    wilderness_coordinates: tuple[int, int] | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
) -> Any:
    """Run one traversal as an all-or-nothing movement settlement.

    ``traverse`` is the exit's own traversal body (design D1). ``destination``
    is the room the traverser will land in when the lineage knows it (the
    plain-exit target and the wilderness grid-return target); its quest-
    observation surfaces (``pin_reasons``, ``interacted``) are snapshotted
    because the wrapped relocation can write them before the charge.
    ``wilderness_coordinates`` and ``wilderness_source_coordinates`` describe
    the wilderness move involved (entry destination, source coordinates); the
    wilderness lineages pass them, which also arms the falsy-return trigger:
    those lineages return real booleans, so a traversal that returns falsy
    after relocating the traverser (a ``move_to`` hook raising after
    relocation) is compensated as a failure. The plain-exit lineage returns
    ``None`` on both branches and never triggers it — ``DefaultExit.at_traverse``
    cannot distinguish success from a relocated failure, so its return value
    stays uninspected (design D1/Non-Goals).

    On an exception the boundary compensates after the outer rollback and
    re-raises; on a falsy relocated return it compensates and returns the
    falsy result, so the WebClient ``move_failed`` / Telnet error paths report
    failure only after the traverser is truthfully back at the source.
    """
    snapshot = _snapshot_movement_state(
        traversing_object,
        source_location,
        destination=destination,
        wilderness_coordinates=wilderness_coordinates,
        wilderness_source_coordinates=wilderness_source_coordinates,
    )
    try:
        with transaction.atomic():
            result = traverse()
    except Exception:
        _compensate_after_rollback(snapshot)
        raise
    wilderness_lineage = (
        wilderness_coordinates is not None or wilderness_source_coordinates is not None
    )
    if (
        not result
        and wilderness_lineage
        and traversing_object.location is not source_location
    ):
        _compensate_after_rollback(snapshot)
    return result


def _snapshot_movement_state(
    traversing_object: Any,
    source_location: Any,
    *,
    destination: Any | None,
    wilderness_coordinates: tuple[int, int] | None,
    wilderness_source_coordinates: tuple[int, int] | None,
) -> MovementSnapshot:
    """Record every pre-move surface the settlement may write (design D2)."""
    from typeclasses.characters import PlayerCharacter

    wilderness = None
    traverser_registration = None
    if wilderness_source_coordinates is not None:
        # A wilderness step or grid-return move: the traverser is already
        # registered, so the involved script is its own registration.
        wilderness = getattr(traversing_object, "ndb", None) and traversing_object.ndb.wilderness
        if wilderness is not None:
            traverser_registration = wilderness.itemcoordinates.get(traversing_object)
    elif wilderness_coordinates is not None:
        # A gate entry: the traverser is not yet registered, so the script is
        # resolved by lookup.
        matches = search_script(WILDERNESS_NAME)
        wilderness = matches[0] if matches else None

    companions: list[CompanionState] = []
    if isinstance(traversing_object, PlayerCharacter):
        for npc in live_companions(traversing_object):
            try:
                if _companion_co_located(npc, source_location, wilderness_source_coordinates):
                    registration = (
                        wilderness.itemcoordinates.get(npc) if wilderness is not None else None
                    )
                    companions.append(CompanionState(npc, npc.location, registration))
            except Exception as error:
                # Mirrors follow_companions' per-NPC exception isolation: a
                # stale or corrupt companion is skipped, never allowed to abort
                # the settlement before it starts.
                log_warn(
                    "movement_companion_snapshot_skipped",
                    exc=error,
                    context={"obj": str(npc)},
                )

    itemcoordinates = rooms = unused_rooms = None
    if wilderness is not None:
        itemcoordinates = dict(wilderness.db.itemcoordinates or {})
        rooms = dict(wilderness.db.rooms or {})
        unused_rooms = list(wilderness.db.unused_rooms or [])

    registry = None
    clock = None
    tick_snapshot = None
    if isinstance(traversing_object, PlayerCharacter):
        clock = get_world_clock()
        # Widened to the one-day advance bound: the exact charge cost is not
        # known here, and a widened window is a strict superset of what the
        # actual advance can write (every registered contract's discovery
        # queries are window-independent today).
        registry = build_advance_snapshot_registry(
            clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (traversing_object,)
        )
        traverser_attrs = {
            (key, None): attribute_snapshot(traversing_object, key)
            for key in _TRAVERSER_SURFACES
        }
        traverser_attrs[("quest_log", None)] = snapshot_quest_log(traversing_object)
        entry = registry.get(id(traversing_object))
        if entry is None:
            registry[id(traversing_object)] = SurfaceSnapshot(attributes=traverser_attrs)
        else:
            entry.attributes.update(traverser_attrs)
        if destination is not None:
            destination_attrs = {
                ("pin_reasons", None): snapshot_pin_reasons(destination),
                ("interacted", None): attribute_snapshot(destination, "interacted"),
            }
            destination_entry = registry.get(id(destination))
            if destination_entry is None:
                registry[id(destination)] = SurfaceSnapshot(attributes=destination_attrs)
            else:
                destination_entry.attributes.update(destination_attrs)
        tick_snapshot = _snapshot_clock_tick(clock)

    return MovementSnapshot(
        traverser=traversing_object,
        source_location=source_location,
        wilderness=wilderness,
        wilderness_coordinates=wilderness_coordinates,
        wilderness_source_coordinates=wilderness_source_coordinates,
        traverser_registration=traverser_registration,
        companions=companions,
        wilderness_itemcoordinates=itemcoordinates,
        wilderness_rooms=rooms,
        wilderness_unused_rooms=unused_rooms,
        registry=registry,
        clock=clock,
        tick_snapshot=tick_snapshot,
    )


def _compensate_after_rollback(snapshot: MovementSnapshot) -> None:
    """Compensate a failed movement without ever masking the original failure."""
    try:
        _compensate(snapshot)
    except Exception as error:
        log_warn(
            "movement_compensation_failed",
            exc=error,
            context={"obj": str(snapshot.traverser)},
        )


def _compensate(snapshot: MovementSnapshot) -> None:
    """Undo a failed movement in the fixed deterministic order (design D3).

    Each step is best-effort with a logged diagnostic; a failure degrades to
    the next step, never silently leaves the primary relocation undone, and
    never masks the original traversal failure.
    """
    _compensate_traverser(snapshot)
    _compensate_home(snapshot)
    _compensate_companions(snapshot)
    _restore_wilderness_bookkeeping(snapshot)
    _restore_surfaces(snapshot)


def _compensate_traverser(snapshot: MovementSnapshot) -> None:
    """Return the traverser to its pre-move location and registration."""
    traverser = snapshot.traverser
    wilderness = snapshot.wilderness
    try:
        registration = (
            wilderness.itemcoordinates.get(traverser) if wilderness is not None else None
        )
        if (
            traverser.location is snapshot.source_location
            and registration == snapshot.traverser_registration
        ):
            return
        if wilderness is not None and snapshot.wilderness_source_coordinates is not None:
            # Wilderness step undo and grid-return undo are the same primitive:
            # re-register at the source coordinates, which also restores the
            # location (the contrib recreates a coordinate-equivalent room when
            # the source room was recycled). A plain move_to back cannot do
            # this for the grid-return case, because the source wilderness room
            # may already be recycled.
            wilderness.move_obj(traverser, snapshot.wilderness_source_coordinates)
        elif wilderness is not None:
            # Gate-entry undo: hook-free return to the grid room, then
            # deregister the traverser from the wilderness bookkeeping (the
            # hook-free move_to never fired the room's at_object_leave hook).
            moved = traverser.move_to(snapshot.source_location, quiet=True, move_hooks=False)
            if moved:
                wilderness.at_post_object_leave(traverser)
        else:
            traverser.move_to(snapshot.source_location, quiet=True, move_hooks=False)
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={
                "stage": "movement_traverser",
                "obj": str(traverser),
                "key": "location",
            },
        )
        _force_reconcile_location(traverser, snapshot.source_location)


def _compensate_home(snapshot: MovementSnapshot) -> None:
    """Reconcile the live traverser's ``home`` after the outer rollback.

    The one-way-gate re-anchor (limbo-one-way-gates D7) may have written the
    traverser's durable ``home`` FK before a later settlement step raised; the
    outer rollback reverted the row but the live object keeps its in-memory
    relation — the same rollback-stale surface class ``db_location`` is treated
    as. The authoritative value is re-read from the rolled-back row and applied
    in-memory only (never a re-assign through the property, which would
    re-save a row the writer did not end up touching).
    """
    from evennia.objects.models import ObjectDB
    from typeclasses.characters import PlayerCharacter

    traverser = snapshot.traverser
    if not isinstance(traverser, PlayerCharacter):
        return
    try:
        row_home = ObjectDB.objects.filter(id=traverser.id).values_list(
            "db_home_id", flat=True
        ).first()
        if traverser.db_home_id != row_home:
            traverser.db_home_id = row_home
    except Exception as error:
        # A home that cannot be reconciled is a diagnostic, never a mask of
        # the original traversal failure (mirrors every other step here).
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"obj": str(traverser), "surface": "home"},
        )


def _compensate_companions(snapshot: MovementSnapshot) -> None:
    """Return every companion the follow step moved back to its pre-move state."""
    wilderness = snapshot.wilderness
    for companion in snapshot.companions:
        npc = companion.npc
        try:
            registration = (
                wilderness.itemcoordinates.get(npc) if wilderness is not None else None
            )
            if npc.location is companion.location and registration == companion.registration:
                continue
            if companion.registration is not None and wilderness is not None:
                # Wilderness-registered companion: re-register at the pre-move
                # coordinates, which also restores the location.
                wilderness.move_obj(npc, companion.registration)
            elif companion.location is not None:
                moved = npc.move_to(companion.location, quiet=True, move_hooks=False)
                if moved and npc.ndb.wilderness is not None:
                    # Mirrors follow_companions leaving the wilderness: clear
                    # any registration the hook-free move_to could not pop.
                    npc.ndb.wilderness.at_post_object_leave(npc)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "movement_companion",
                    "obj": str(npc),
                    "key": "location",
                },
            )
            _force_reconcile_location(npc, companion.location)


def _restore_wilderness_bookkeeping(snapshot: MovementSnapshot) -> None:
    """Restore the wilderness script's in-memory bookkeeping (design D3 step 3).

    Mandatory, not optional: the outer rollback deletes freshly created
    room/exit rows, but the in-memory bookkeeping keeps them, and a preceding
    ``at_post_object_leave`` on a gate-entry undo would append the rolled-back
    zombie room to ``unused_rooms``, poisoning the next ``_create_room`` pop.
    The shallow snapshots are written back directly because the shared restore
    helper would ``deepcopy`` live Evennia objects.
    """
    wilderness = snapshot.wilderness
    if wilderness is None:
        return
    for key, value in (
        ("itemcoordinates", snapshot.wilderness_itemcoordinates),
        ("rooms", snapshot.wilderness_rooms),
        ("unused_rooms", snapshot.wilderness_unused_rooms),
    ):
        if value is None:
            continue
        try:
            setattr(wilderness.db, key, value)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={"stage": "movement_wilderness", "obj": "wilderness", "key": key},
            )


def _restore_surfaces(snapshot: MovementSnapshot) -> None:
    """Restore the clock tick and every snapshotted surface (design D3 step 5)."""
    if snapshot.registry is None:
        return
    try:
        if snapshot.tick_snapshot is not None:
            _restore_clock_tick(snapshot.clock, snapshot.tick_snapshot)
        # The clock module's canonical registry restore rewrites each durable
        # attribute (refreshing the backend cache), re-fetches recorded
        # locations by primary key and assigns through the location setter so
        # the contents caches reconcile, flushes cached-but-deleted instances,
        # and refreshes the traverser's trait/sexual caches.
        _restore_advance_registry(snapshot.registry, (snapshot.traverser,))
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={
                "stage": "movement_advance_surfaces",
                "obj": str(snapshot.traverser),
                "key": "registry",
            },
        )


def _force_reconcile_location(obj: Any, target: Any) -> None:
    """Force-reconcile Evennia's in-process location surfaces (design D3 step 4).

    Fallback for a relocation that failed or raised: assign ``db_location``
    through the location property (which performs the same contents add/remove
    as ``move_to`` and persists), then belt-and-braces re-initialize the
    target's and the object's previous room's ``contents_cache``.
    """
    try:
        previous = obj.location
        obj.location = target
        target.contents_cache.init()
        if previous is not None and previous is not target:
            previous.contents_cache.init()
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "movement_reconcile", "obj": str(obj), "key": "location"},
        )
