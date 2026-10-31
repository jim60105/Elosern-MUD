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
failure surfaces: the traverser and every follower (companions, and the
commander's body under possession) are moved back, the wilderness
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

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from django.db import transaction
from evennia.utils.search import search_script

from world.maps.area_identity import is_alignment_boundary, read_alignment_identity
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
from world.rules.party import follow_scope
from world.rules.presentation_events import (
    AlignmentIdentity,
    PresentationAlignmentFact,
    current_publication_group,
    emit_alignment_fact,
    new_publication_group,
    on_publication_commit,
    publication_group,
)
from world.rules.surfaces import attribute_snapshot

# Move-observable attribute surfaces the settlement can write on the traverser
# or the commander behind a possessed traverser, snapshotted directly (the
# advance registry covers the remainder). ``wallet``/``inventory``/
# ``guild_reward_claims`` are the AUTO quest-settlement payout surfaces the
# arrival observation can write; ``quest_log`` and the destination room's
# pin/state surfaces use the quest module's own helpers so the two writers
# never drift.
_TRAVERSER_SURFACES: tuple[str, ...] = (
    "map_knowledge",
    "wallet",
    "inventory",
    "guild_reward_claims",
    # The arrival observation's replacement writer also settles the
    # completion's quest-completed fixed titles; a later movement failure must
    # return those caches with every other surface.
    "title_collection",
    "title_equipped",
)


@dataclass
class CompanionState:
    """One co-located follower's pre-move location and wilderness registration.

    A follower is an effective companion or, under possession, the commander's
    own body. ``registration`` is the script's ``itemcoordinates`` entry (a
    coordinate tuple) when the follower was tracked in the wilderness, else
    ``None``.
    """

    entity: Any
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
    ``None`` for non-player-driven traversers, whose settlement steps are
    internal no-ops. ``commander`` is the player behind a possessed traverser
    (``None`` when there is none); its body is part of ``companions`` and its
    map-knowledge and quest surfaces are registered for restoration.
    """

    traverser: Any
    source_location: Any
    wilderness: Any
    wilderness_coordinates: tuple[int, int] | None
    wilderness_source_coordinates: tuple[int, int] | None
    traverser_registration: tuple[int, int] | None
    companions: list[CompanionState]
    commander: Any | None
    wilderness_itemcoordinates: dict | None
    wilderness_rooms: dict | None
    wilderness_unused_rooms: list | None
    registry: dict[int, SurfaceSnapshot] | None
    clock: Any
    tick_snapshot: Any


# ---------------------------------------------------------------------------
# Committed alignment checkpoints (webclient-movement-alignment).
#
# The deterministic movement owner is the only place a relocation is known to
# have committed, so it is also the only place a movement checkpoint fact may
# be captured. Capture is read-only: these helpers copy authoritative
# identities into frozen values and hand one fact to the presentation layer's
# registered observer. Nothing here mutates game state, builds a publication,
# or imports the webclient.
# ---------------------------------------------------------------------------


#: Traversers whose relocation the running settlement will publish itself.
_settlement_owners: contextvars.ContextVar[tuple[int, ...]] = contextvars.ContextVar(
    "elosern_movement_settlement_owners", default=()
)

#: Source identities of direct moves no settlement owns, per actor id.
_direct_move_sources: contextvars.ContextVar[
    tuple[tuple[int, AlignmentIdentity | None], ...]
] = contextvars.ContextVar("elosern_direct_move_sources", default=())


@contextmanager
def settlement_scope(actor: Any) -> Iterator[None]:
    """Mark that the movement settlement owns ``actor``'s relocation here.

    ``PlayerCharacter`` also captures direct moves in its own move hooks; the
    scope lets that hook stand down for exactly the actors the settlement will
    publish, so one traversal emits one fact. The marker is per actor, so an
    unrelated actor moved inside the same synchronous chain (a follower, a
    possessed body, a second player) keeps its own capture.
    """
    actor_id = int(actor.pk)
    token = _settlement_owners.set(_settlement_owners.get() + (actor_id,))
    try:
        yield
    finally:
        _settlement_owners.reset(token)


def settlement_owns_movement(actor: Any) -> bool:
    """Whether the running settlement publishes ``actor``'s relocation."""
    return int(actor.pk) in _settlement_owners.get()


def publish_movement_boundary(
    actor: Any,
    source_identity: AlignmentIdentity | None,
    destination_identity: AlignmentIdentity | None,
) -> None:
    """Publish one committed movement checkpoint when the transition crossed.

    Both identities are already-copied values: ``source_identity`` was read
    before the traversal (so a pooled room mutated by it cannot rewrite the
    source) and ``destination_identity`` was read after the settled relocation
    and any compensation (so a failure or a rollback that restored the source
    position cannot publish a boundary). Only the *emission* waits for the
    surrounding transaction, so a rolled-back outer transaction still emits
    nothing, while a same-area relocation emits nothing at all.
    """
    if not is_alignment_boundary(source_identity, destination_identity):
        return
    actor_id = int(actor.pk)

    def _committed() -> None:
        group = current_publication_group() or new_publication_group()
        emit_alignment_fact(
            PresentationAlignmentFact(
                group_id=group.id,
                actor_id=actor_id,
                cause="movement_boundary",
                source=source_identity,
                destination=destination_identity,
            )
        )

    on_publication_commit(_committed)


def note_direct_move_start(actor: Any) -> None:
    """Copy the source identity of a direct move no settlement owns."""
    if settlement_owns_movement(actor):
        return
    actor_id = int(actor.pk)
    identity = read_alignment_identity(actor)
    kept = tuple(entry for entry in _direct_move_sources.get() if entry[0] != actor_id)
    _direct_move_sources.set(kept + ((actor_id, identity),))


def note_direct_move_end(actor: Any) -> None:
    """Publish the committed checkpoint of a direct move, at most once."""
    if settlement_owns_movement(actor):
        return
    actor_id = int(actor.pk)
    sources = _direct_move_sources.get()
    for index, (key, identity) in enumerate(sources):
        if key != actor_id:
            continue
        _direct_move_sources.set(sources[:index] + sources[index + 1 :])
        publish_movement_boundary(actor, identity, read_alignment_identity(actor))
        return


# ---------------------------------------------------------------------------
# Ephemeral interrupt observations (wilderness-travel-interrupts).
#
# The adapter binds one collector around its exit traversal only. The
# settlement captures the immutable before facts before the traversal and the
# after facts only once a settled relocation is known, so a refused, failed or
# compensated step can never publish an interrupt result. The collector holds
# values and a ContextVar binding, never game state, and the adapter reads the
# frozen flag tuple after `at_traverse` returns.
# ---------------------------------------------------------------------------


class MovementObservation:
    """One move's ephemeral before/after interrupt facts.

    The collector is actor-scoped: a nested settlement for another actor (an
    NPC moved inside the same synchronous chain) resolves no collector and
    therefore can neither replace this actor's step nor publish its facts.
    Every capture or comparison failure is reported as
    ``travel_interrupts_failed`` and leaves the empty-flag disposition, so a
    broken read never fails an otherwise successful movement.
    """

    __slots__ = ("actor_id", "walk", "before", "after", "flags", "wilderness", "_members", "_tick")

    def __init__(self, actor: Any, walk: Any = None) -> None:
        self.actor_id = int(actor.pk)
        self.walk = walk
        self.before: Any = None
        self.after: Any = None
        self.flags: tuple[str, ...] = ()
        self.wilderness = False
        self._members: tuple[Any, ...] = ()
        self._tick = 0

    def capture_before(
        self,
        actor: Any,
        source_location: Any,
        *,
        wilderness_source_coordinates: tuple[int, int] | None,
        knowledge_owner: Any,
    ) -> None:
        """Freeze the facts of the position being left, before any write."""
        from world.rules import travel_interrupts
        from world.rules.clock import read_world_clock

        try:
            # Record the correlation tick before the rest of the read, so a
            # later capture failure still reports the real world time.
            clock = read_world_clock()
            self._tick = 0 if clock is None else int(clock.tick)
            self._members = travel_interrupts._source_present_members(
                actor, source_location, wilderness_source_coordinates
            )
            facts = travel_interrupts.read_movement_facts(
                actor,
                source_location,
                cell=wilderness_source_coordinates,
                knowledge_owner=knowledge_owner,
                members=self._members,
            )
        except Exception as error:  # observability: ignore R2: the failure IS reported by _failed's travel_interrupts_failed event below; an interrupt read must never fail a committed move
            self._failed(error, "before")
            return
        self.before = facts
        self._tick = facts.tick

    def capture_after(self, actor: Any, *, knowledge_owner: Any) -> None:
        """Compare the committed destination facts with the frozen source facts."""
        from world.rules import travel_interrupts

        try:
            # The setup is part of the capture: a destination-coordinate read
            # failure must never escape a committed move.
            location = getattr(actor, "location", None)
            cell = travel_interrupts.wilderness_cell(location)
            if cell is None:
                return
            self.wilderness = True
            if self.before is None:
                # The source capture already reported its failure.
                return
            after = travel_interrupts.read_movement_facts(
                actor,
                location,
                cell=cell,
                knowledge_owner=knowledge_owner,
                members=self._members,
            )
            self.after = after
            self._tick = after.tick
            self.flags = travel_interrupts.movement_flags(
                self.before, after, walk=self.walk
            )
        except Exception as error:  # observability: ignore R2: the failure IS reported by _failed's travel_interrupts_failed event below; an interrupt comparison must never fail a committed move
            self._failed(error, "after")

    def _failed(self, error: Exception, step: str) -> None:
        self.flags = ()
        log_warn(
            "travel_interrupts_failed",
            context={"char": self.actor_id, "tick": self._tick, "step": step},
            exc=error,
        )


_movement_observation: contextvars.ContextVar[MovementObservation | None] = (
    contextvars.ContextVar("elosern_movement_observation", default=None)
)


@contextmanager
def capture_movement_observation(
    actor: Any, *, walk: Any = None
) -> Iterator[MovementObservation]:
    """Bind one ephemeral interrupt collector around one move's traversal."""
    observation = MovementObservation(actor, walk)
    token = _movement_observation.set(observation)
    try:
        yield observation
    finally:
        _movement_observation.reset(token)


def _observation_for(actor: Any) -> MovementObservation | None:
    """The collector bound for exactly ``actor``'s step, or ``None``."""
    observation = _movement_observation.get()
    if observation is None:
        return None
    if observation.actor_id != int(actor.pk):
        return None
    return observation


def settle_movement(
    traversing_object: Any,
    source_location: Any,
    *,
    traverse: Callable[[], Any],
    destination: Any | None = None,
    wilderness_coordinates: tuple[int, int] | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    window_seconds: int | None = None,
    narrate_traversal: bool = False,
) -> Any:
    """Run one traversal as an all-or-nothing movement settlement.

    ``traverse`` is the exit's own traversal body (design D1). ``destination``
    is the room the traverser will land in when the lineage knows it (the
    plain-exit target and the wilderness grid-return target); its quest-
    observation surfaces (``pin_reasons``, ``interacted``) are snapshotted
    because the wrapped relocation can write them before the charge.
    The charge itself is the exit's pre-relocation physical-duration record
    (``world.rules.travel_cost::preflight_movement_cost``), so the settlement
    transaction never re-derives a cost from post-relocation room state; the
    commit/compensation guarantees below are unchanged.
    ``wilderness_coordinates`` and ``wilderness_source_coordinates`` describe
    the wilderness move involved (entry destination, source coordinates); the
    wilderness lineages pass them, which also arms the falsy-return trigger:
    those lineages return real booleans, so a traversal that returns falsy
    after relocating the traverser (a ``move_to`` hook raising after
    relocation) is compensated as a failure. The plain-exit lineage returns
    ``None`` on both branches and never triggers it — ``DefaultExit.at_traverse``
    cannot distinguish success from a relocated failure, so its return value
    stays uninspected (design D1/Non-Goals).

    ``window_seconds`` is the preflight record's committed traversal duration.
    The clock charge of a long edge runs bounded internal advances inside this
    same outer transaction, so the pre-advance registry is built for at least
    that full window (never less than the one-day single-call bound); a failure
    in any internal advance restores every surface the whole traversal may have
    written.

    On an exception the boundary compensates after the outer rollback and
    re-raises; on a falsy relocated return it compensates and returns the
    falsy result, so the WebClient ``move_failed`` / Telnet error paths report
    failure only after the traverser is truthfully back at the source.
    """
    if narrate_traversal:
        from world.rules.map_discovery import visited_before_traversal, traversal_node_id

        before = visited_before_traversal(traversing_object)
        source_node = traversal_node_id(traversing_object, source_location)
    # The committed area/instance identity of the position being left. It is
    # read before the traversal, so a pooled room the move recycles or mutates
    # cannot rewrite which area the traverser left.
    source_identity = read_alignment_identity(traversing_object)
    # Every panel push, checkpoint fact and settlement callback of this
    # traversal shares one causal publication group, so each watcher receives
    # one final publication for the commit (webclient-publication-settlements).
    with publication_group(), settlement_scope(traversing_object):
        snapshot = _snapshot_movement_state(
            traversing_object,
            source_location,
            destination=destination,
            wilderness_coordinates=wilderness_coordinates,
            wilderness_source_coordinates=wilderness_source_coordinates,
            window_seconds=window_seconds,
        )
        observation = _observation_for(traversing_object)
        if observation is not None:
            # Frozen immediately before the traversal and before any pooled-room
            # mutation: the source cell and the party's before physiology can
            # never be rewritten by the step they describe.
            observation.capture_before(
                traversing_object,
                source_location,
                wilderness_source_coordinates=wilderness_source_coordinates,
                knowledge_owner=snapshot.commander or traversing_object,
            )
        try:
            from world.quests.escort_events import escort_event_boundary

            with escort_event_boundary((
                traversing_object, *(state.entity for state in snapshot.companions),
            )), transaction.atomic():
                result = traverse()
                # A published encounter whose declared locator covers the settled
                # position activates here, inside the owning movement transaction
                # and before the boundary's trailing final escort/outcome
                # evaluation, so a meeting role exists before the shared evaluator
                # observes the resulting position (dream-story-dispatch §7). The
                # pass never raises: a refused encounter store can never cancel a
                # completed move.
                from world.quests.encounter_dispatch import activate_pending_encounters

                activate_pending_encounters(
                    traversing_object,
                    room=getattr(traversing_object, "location", None),
                    tick=int(get_world_clock().tick),
                )
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
        settled = traversing_object.location is not source_location
        if wilderness_lineage and result and not settled:
            # A terrain room is a pooled view over coordinates: a successful
            # step may stay on the same room object while the traverser moved to
            # another cell. The wilderness identity is the registered map, so
            # this can never fake a boundary inside one continuous area.
            settled = True
        if settled:
            # A settled relocation: any dialogue the character was holding
            # belongs to the room it left (webclient-align-07). Checked against
            # the post-compensation location, so a falsy wilderness return that
            # was moved back never clears; the plain-exit lineage returns
            # ``None`` on both branches, so the location is the only reliable
            # success signal.
            from world.rules.dialogue import clear_dialogue_session

            # The moving actor owns the session, including a possessed companion
            # acting through the transferred puppet.
            clear_dialogue_session(traversing_object)
            # The committed checkpoint, captured only for a settled relocation:
            # a refusal, a rollback or a compensated falsy return publishes
            # nothing, and a same-area move stays incremental.
            publish_movement_boundary(
                traversing_object,
                source_identity,
                read_alignment_identity(traversing_object),
            )
            if observation is not None:
                # Only a settled relocation has an after state to compare: a
                # refusal, a rollback or a compensated falsy return keeps the
                # collector's empty-flag disposition.
                observation.capture_after(
                    traversing_object,
                    knowledge_owner=snapshot.commander or traversing_object,
                )
        if narrate_traversal and not (wilderness_lineage and not result):
            from world.rules.map_discovery import publish_traversal_narrative

            if traversal_node_id(traversing_object, traversing_object.location) != source_node:
                publish_traversal_narrative(traversing_object, before)
        return result


def settle_relocation(entity: Any, destination: Any) -> None:
    """Relocate one operator-selected entity with its arrival bookkeeping.

    The operator console's map-lifecycle ``teleport`` verb
    (gm-developer-console::map-lifecycle-verbs-with-consequences): the entity
    moves without a movement charge, records its arrival node, brings its
    party along, observes the destination's arrival lore, re-homes a gate
    arrival, and drops the dialogue it held in the room it left. Every write
    lives in this deterministic settlement, so the operator adapter delegates
    instead of importing a map-knowledge write helper (map-knowledge D4).

    A refused move compensates and raises the console's ``movement_refused``
    error; any later failure compensates after the outer rollback and
    re-raises, exactly as the adapter did when it owned this body. Its
    evidence is ``world/maps/tests/test_gm.py``, which drives the verb and
    asserts the arrival, party, dialogue and rollback consequences.
    """
    from server.console.errors import ConsoleError
    from typeclasses.characters import PlayerCharacter
    from world.quests.room_observation import observe_arrival_lore
    from world.rules.city_gates import reanchor_home_on_gate_arrival
    from world.rules.dialogue import clear_dialogue_session
    from world.rules.map_knowledge import record_arrival
    from world.rules.party import follow_companions
    from world.rules.surfaces import restore_attributes, snapshot_attributes

    source = entity.location
    source_wilderness = getattr(source, "wilderness", None)
    # Capture before the move: the contrib deletes a recycled source room's
    # active coordinates, so reading them afterwards yields None.
    source_coordinates = (
        source.coordinates if source_wilderness is not None else None
    )
    # The committed identity of the position being left, copied before any
    # write (the same reason the coordinates above are captured here).
    source_identity = read_alignment_identity(entity)
    with publication_group(), settlement_scope(entity):
        snapshot = _snapshot_movement_state(
            entity,
            source,
            destination=destination,
            wilderness_coordinates=None,
            wilderness_source_coordinates=source_coordinates,
        )
        attrs = snapshot_attributes(entity, ("dialogue_session",))
        try:
            with transaction.atomic():
                destination_wilderness = getattr(destination, "wilderness", None)
                if destination_wilderness is not None:
                    # A terrain room is a pooled view over coordinates: a plain
                    # move_to runs the contrib's receive hook without the extra
                    # move kwargs and leaves the entity registered at its old
                    # cell. Gate explicitly, then enter through the provider API.
                    if not destination.at_pre_object_receive(entity, source):
                        raise ConsoleError("invalid_argument", "movement_refused")
                    from evennia.contrib.grid.wilderness.wilderness import (
                        enter_wilderness,
                    )

                    moved = enter_wilderness(
                        entity,
                        coordinates=destination.coordinates,
                        name=destination_wilderness.db_key or WILDERNESS_NAME,
                    )
                else:
                    moved = entity.move_to(destination, quiet=True, move_type="teleport")
                if not moved:
                    raise ConsoleError("invalid_argument", "movement_refused")
                record_arrival(entity)
                follow_companions(
                    entity,
                    source,
                    destination=destination,
                    wilderness_source_coordinates=source_coordinates,
                )
                observe_arrival_lore(entity, destination)
                reanchor_home_on_gate_arrival(entity, destination)
                if source is not destination:
                    clear_dialogue_session(entity)
                # Registered last inside the owning transaction: any later
                # failure rolls the relocation back together with this
                # checkpoint, so a refused or failed teleport publishes nothing.
                publish_movement_boundary(
                    entity,
                    source_identity,
                    read_alignment_identity(entity),
                )
        except Exception:
            _compensate(snapshot)
            restore_attributes(entity, attrs)
            raise


def _snapshot_movement_state(
    traversing_object: Any,
    source_location: Any,
    *,
    destination: Any | None,
    wilderness_coordinates: tuple[int, int] | None,
    wilderness_source_coordinates: tuple[int, int] | None,
    window_seconds: int | None = None,
) -> MovementSnapshot:
    """Record every pre-move surface the settlement may write (design D2)."""
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
    if wilderness is None:
        # A non-exit relocation (operator teleport) can leave or enter the
        # wilderness without coordinate arguments; resolve the involved script
        # from the source or destination room so the traverser's registration
        # and the script's bookkeeping are still snapped and restored.
        wilderness = getattr(source_location, "wilderness", None) or getattr(
            destination, "wilderness", None
        )
    itemcoordinates_prop = getattr(wilderness, "itemcoordinates", None)
    if wilderness is not None and traverser_registration is None:
        traverser_registration = itemcoordinates_prop.get(traversing_object) if itemcoordinates_prop else None

    commander, followers = follow_scope(
        traversing_object,
        source_location,
        wilderness_source_coordinates,
        log_unresolved=False,
    )
    companions: list[CompanionState] = []
    for follower in followers:
        try:
            registration = (
                itemcoordinates_prop.get(follower) if itemcoordinates_prop else None
            )
            companions.append(CompanionState(follower, follower.location, registration))
        except Exception as error:
            # Mirrors follow_companions' per-follower exception isolation: a
            # stale or corrupt follower is skipped, never allowed to abort the
            # settlement before it starts.
            log_warn(
                "movement_companion_snapshot_skipped",
                exc=error,
                context={"obj": str(follower)},
            )

    itemcoordinates = rooms = unused_rooms = None
    if wilderness is not None and hasattr(wilderness, "db"):
        itemcoordinates = dict(wilderness.db.itemcoordinates or {})
        rooms = dict(wilderness.db.rooms or {})
        unused_rooms = list(wilderness.db.unused_rooms or [])

    registry = None
    clock = None
    tick_snapshot = None
    from world.rules.player_control import is_player_driven

    if is_player_driven(traversing_object):
        clock = get_world_clock()
        # The one-day advance bound is the floor; a longer committed edge
        # widens the window to its full planned duration, so a registered
        # contract whose surface falls due late in the traversal is still
        # snapshotted even though the charge advances in bounded pieces.
        window = max(MAX_ADVANCE_SECONDS, window_seconds or 0)
        # The travelling party is exactly the set the charge and the follow
        # step settle: the traverser plus every follower resolved from the
        # pre-move source. The preflight record's traveller tuple is reused
        # when the exit opened this settlement, so the snapshot, the speed,
        # the admission and the charge can never disagree about the scope.
        from world.rules.travel_cost import active_traversal_members

        priced_members = active_traversal_members(
            traversing_object, source_location
        )
        snapshot_entities = list(
            priced_members
            if priced_members is not None
            else (
                traversing_object,
                *(state.entity for state in companions),
            )
        )
        registry = build_advance_snapshot_registry(
            clock, window, AdvanceSource.COMMAND, snapshot_entities
        )
        for entity in snapshot_entities:
            entity_attrs = {
                (key, None): attribute_snapshot(entity, key)
                for key in _TRAVERSER_SURFACES
            }
            if getattr(entity, "quest_log", None) is not None:
                entity_attrs[("quest_log", None)] = snapshot_quest_log(entity)
            entry = registry.get(id(entity))
            if entry is None:
                registry[id(entity)] = SurfaceSnapshot(attributes=entity_attrs)
            else:
                entry.attributes.update(entity_attrs)
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
        commander=commander,
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
    _restore_wilderness_rooms(snapshot)
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
        restored_coordinates = (
            snapshot.wilderness_source_coordinates
            if snapshot.wilderness_source_coordinates is not None
            else snapshot.traverser_registration
        )
        if wilderness is not None and restored_coordinates is not None:
            # Wilderness step undo, grid-return undo, and the undo of a
            # non-exit relocation that stayed in the wilderness are the same
            # primitive: re-register at the pre-move coordinates, which also
            # restores the location (the contrib recreates a
            # coordinate-equivalent room when the source room was recycled). A
            # plain move_to back cannot do this for the grid-return case,
            # because the source wilderness room may already be recycled.
            wilderness.move_obj(traverser, restored_coordinates)
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
    """Return every follower the follow step moved to its pre-move state.

    The list includes the commander's own body under possession; the body's
    restoration is the same hook-free relocation or coordinate-API primitive.
    """
    wilderness = snapshot.wilderness
    for companion in snapshot.companions:
        entity = companion.entity
        try:
            registration = (
                wilderness.itemcoordinates.get(entity) if wilderness is not None else None
            )
            if entity.location is companion.location and registration == companion.registration:
                continue
            if companion.registration is not None and wilderness is not None:
                # Wilderness-registered companion: re-register at the pre-move
                # coordinates, which also restores the location.
                wilderness.move_obj(entity, companion.registration)
            elif companion.location is not None:
                moved = entity.move_to(companion.location, quiet=True, move_hooks=False)
                if moved and entity.ndb.wilderness is not None:
                    # Mirrors follow_companions leaving the wilderness: clear
                    # any registration the hook-free move_to could not pop.
                    entity.ndb.wilderness.at_post_object_leave(entity)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "movement_companion",
                    "obj": str(entity),
                    "key": "location",
                },
            )
            _force_reconcile_location(entity, companion.location)


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
    if wilderness is None or not hasattr(wilderness, "db"):
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


def _restore_wilderness_rooms(snapshot: MovementSnapshot) -> None:
    """Reconcile room allocation, active coordinates, and registered occupants.

    Restoring the bookkeeping dicts alone is not coherent: compensation may
    have re-used a pooled room for a different coordinate (``move_obj`` pops
    ``unused_rooms``), so the restored ``rooms`` map can name one room while
    the party sits in another that claims the same coordinate. Re-bind every
    snapshotted room to its recorded coordinate (or recycled state), then put
    every registered entity into the room the restored map names, so
    ``rooms[coordinates] is member.location`` holds after a rollback. Runs
    after the dict restore and before the attribute surfaces; best-effort per
    room and per entity, never masking the original failure.
    """
    wilderness = snapshot.wilderness
    if wilderness is None:
        return
    rooms = snapshot.wilderness_rooms or {}
    for coordinates, room in rooms.items():
        if room is None:
            continue
        try:
            room.ndb.wildernessscript = wilderness
            room.ndb.active_coordinates = coordinates
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "movement_wilderness_room",
                    "obj": str(room),
                    "key": "active_coordinates",
                },
            )
    for room in snapshot.wilderness_unused_rooms or []:
        if room is None:
            continue
        try:
            room.ndb.wildernessscript = wilderness
            if getattr(room.ndb, "active_coordinates", None) is not None:
                del room.ndb.active_coordinates
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "movement_wilderness_room",
                    "obj": str(room),
                    "key": "unused_rooms",
                },
            )
    for entity, coordinates in (snapshot.wilderness_itemcoordinates or {}).items():
        if entity is None:
            continue
        room = rooms.get(coordinates)
        if room is None:
            continue
        try:
            if entity.location is not room:
                entity.location = room
            entity.ndb.wilderness = wilderness
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "movement_wilderness_occupant",
                    "obj": str(entity),
                    "key": "location",
                },
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
        # and refreshes the restored entities' trait/sexual caches.
        # Restore the same travelling party the registry was built from, so
        # every settled member's gauges, buffs, and practice booking roll back
        # together (party-rest-move-settlement).
        restore_entities = [
            snapshot.traverser,
            *(state.entity for state in snapshot.companions),
        ]
        _restore_advance_registry(snapshot.registry, tuple(restore_entities))
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
