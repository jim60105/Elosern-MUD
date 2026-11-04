"""Persistent individual-based regional monster population owner.

This module is the single writer of a wilderness world's regional population.
It owns the durable per-zone selection state (``regional_population``), the
explicitly initialized shared world seed (``regional_population_seed``), the
deterministic planning and atomic committing of complete birth waves, and the
one explicit placement registration other owners use for lawful manual and
quest wilderness placements.

Ownership boundary (the ``regional-population`` capability):

* An ordinary individual born here carries ``db.home_ecology_zone`` -- its
  durable home ownership, independent of where it currently stands -- plus the
  ordinary species/variant identity. Its persistent dbref is its identity; no
  cell or slot key is assigned, and nothing in this module ever replaces a
  living survivor.
* Membership is discovered, never stored in a roster: local counts read every
  living ``Monster`` physically inside the zone's rectangles intersected with
  its parent terrain region (including excluded-buffer cells, and including
  ambient, manual, site and quest visitors); home counts read every living
  individual carrying the home marker wherever it is, which is why a
  travelling or detached owner still consumes home headroom while counting
  locally only where it actually stands.
* Reading is side-effect free. ``population_counts`` and
  ``plan_population_wave`` never write, create, move, delete, or emit an event.

Birth eligibility (which cells may host an ordinary birth) belongs to the
already-published ecology layer: :func:`world.maps.population_geometry.
eligible_birth_cells` and :func:`~world.maps.population_geometry.density_bounds`
decide cell eligibility and the local band ``[L, U]``. This module only fits
complete compositions inside the remaining budgets.

Deterministic selection uses one SHA-256 stream per draw, over canonical bytes
of ``(seed, zone_key, generation_sequence, tick, placement_ordinal, purpose,
draw_ordinal)`` with rejection sampling. No Python ``hash``, no global random
state, and no wall clock participate, so replaying the same occurrence inputs
under the same state selects the same complete plan.

Every wave commits inside one ``transaction.atomic()``: the complete composed
group, its home markers, its coordinate registrations, any active-room
attachment, and the incremented selection state. A failure at any point -- and
a later failure of an enclosing transaction through the exported surface
snapshot/restore pair -- restores the durable values and the live Evennia
caches (SaverDict values, room contents caches, and rolled-back idmapper
instances), so no partial group, stray registration, or forged success event
survives.

This slice supplies the callable owner operations only. No production clock
stage or ambient branch is registered here; ``regional-population-recovery``
extends the same state with recovery timing, and
``regional-population-runtime-cutover`` activates the stage.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from django.db import transaction
from evennia.contrib.grid.wilderness.wilderness import WildernessScript
from evennia.utils.dbserialize import from_pickle, to_pickle

from elosern_map_core.terrain import region_for_coordinates

from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    ECOLOGY_ZONE_REGISTRY,
    ENCOUNTER_COMPOSITION_REGISTRY,
    SETTLEMENT_BIRTH_POLICY_REGISTRY,
    EcologyZone,
    EncounterComposition,
    variant_species_key,
)
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.population_geometry import density_bounds, eligible_birth_cells
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_info, log_warn
from world.rules.clock import ScheduledEvent, SurfaceSnapshot
from world.rules.monster_individual import construct_species_individual
from world.rules.surfaces import persisted_hp

#: The world seed a freshly provisioned wilderness script starts with. It is an
#: explicit configured value, never an implicit default for a missing seed: an
#: existing script that has no saved seed refuses to guess.
INITIAL_POPULATION_SEED = 0

#: The wilderness Attribute holding the whole per-zone durable state map.
REGIONAL_POPULATION_ATTRIBUTE = "regional_population"

#: The wilderness Attribute holding the one explicitly initialized shared seed.
POPULATION_SEED_ATTRIBUTE = "regional_population_seed"

#: The wilderness Attribute holding the chronological presence evidence.
POPULATION_TIMELINE_ATTRIBUTE = "population_timeline"

#: The individual Attribute carrying ordinary home ownership.
HOME_ZONE_ATTRIBUTE = "home_ecology_zone"

#: The wilderness Attribute holding every object's registered coordinate.
ITEMCOORDINATES_ATTRIBUTE = "itemcoordinates"

#: The named refusals this owner answers with. A missing world and malformed
#: owner state are distinct from a temporarily blocked birth space.
WORLD_UNAVAILABLE = "world_unavailable"
UNKNOWN_ZONE = "unknown_zone"
MALFORMED_STATE = "malformed_state"
STATE_UNINITIALIZED = "population_state_uninitialized"
SEED_UNINITIALIZED = "population_seed_uninitialized"
SEED_MISMATCH = "population_seed_mismatch"
STALE_PLAN = "stale_plan"
PLACEMENT_REFUSED = "explicit_placement_refused"

#: The hint appended to the uninitialized-seed refusal.
PERSISTED_SEED_HINT = f"no saved {POPULATION_SEED_ATTRIBUTE!r}"

#: The closed vocabulary of ``PopulationWavePlan.blocked_reason``. A blocked
#: plan is lawful (temporary) space pressure, never an authoring defect:
#: ``uninitialized`` means no committed zone state exists yet, the two
#: ``*_satisfied``/``*_saturated`` reasons mean an individual ceiling is already
#: reached, and ``no_legal_space`` means no complete composition fits the
#: remaining budgets or no unprotected cell has room for one.
BLOCKED_UNINITIALIZED = "uninitialized"
BLOCKED_LOCAL_SATISFIED = "local_satisfied"
BLOCKED_HOME_SATURATED = "home_saturated"
BLOCKED_NO_LEGAL_SPACE = "no_legal_space"

#: Draw purposes. Each purpose owns its own draw ordinals, so adding a draw to
#: one selection step cannot shift another step's outcome.
_PURPOSE_CELL = "cell"
_PURPOSE_COMPOSITION = "composition"
_PURPOSE_COUNTS = "counts"
#: The occurrence purpose of an explicit manual site's complete composition.
#: A site's occurrence is identified by its saved seed, its own key and its
#: generation sequence, so a retry at a later in-game tick reproduces the same
#: group; the draw therefore never reads a tick.
_PURPOSE_SITE_COUNTS = "site_counts"

_DRAW_BYTES = 8
_DRAW_SPACE = 1 << (_DRAW_BYTES * 8)


class RegionalPopulationError(RuntimeError):
    """Base class for this owner's operational refusals."""


class RegionalPopulationWorldUnavailable(RegionalPopulationError):
    """No wilderness world exists to own this population."""


class UnknownEcologyZone(RegionalPopulationError):
    """The named zone is not an authored ecology zone."""


class MalformedPopulationState(RegionalPopulationError):
    """The durable population state is present but unusable."""


class PopulationStateUninitialized(RegionalPopulationError):
    """A preexisting world lacks the required initialized population state."""


class PopulationSeedUninitialized(RegionalPopulationError):
    """The shared world seed was never explicitly initialized (or is unusable)."""


class PopulationSeedMismatch(RegionalPopulationError):
    """A zone initialization asked for a seed other than the saved world seed."""


class PopulationPlanStale(RegionalPopulationError):
    """A wave plan no longer matches the committed state it was planned from."""


class ExplicitPlacementRefused(RegionalPopulationError):
    """An explicit placement is not on a valid wilderness surface."""


@dataclass(frozen=True, slots=True)
class ZonePopulationState:
    """One zone's committed population selection state."""

    zone_key: str
    seed: int
    generation_sequence: int
    recovery_due_tick: int | None
    settled_through_tick: int


@dataclass(frozen=True, slots=True)
class PopulationCounts:
    """The three independent individual measures of one zone.

    ``local_ids`` are living individuals physically inside the zone (all
    ownership kinds); ``home_ids`` are living individuals bearing this zone's
    home marker wherever they currently are; ``cell_ids`` maps each occupied
    local cell to its living occupants, in persistent-ID sets so one object is
    counted once per measure. All three are read-only snapshots; nothing here
    repairs, relocates or deletes a foreign individual.
    """

    local_ids: frozenset[int]
    home_ids: frozenset[int]
    cell_ids: Mapping[tuple[int, int], frozenset[int]]


@dataclass(frozen=True, slots=True)
class PopulationPlacement:
    """One complete composition placed at one cell.

    ``groups`` is the composition's member order, so a caller reading the
    placement sees the authored group shape; the sum of the counts is the
    number of individuals the placement creates.
    """

    cell: tuple[int, int]
    groups: tuple[tuple[str, int], ...]

    @property
    def total(self) -> int:
        return sum(count for _variant, count in self.groups)


@dataclass(frozen=True, slots=True)
class PopulationWavePlan:
    """One deterministic wave decision.

    A successful wave places exactly one complete composition (``placements``
    has one entry); a blocked wave places nothing and carries its named reason.
    ``expected_seed``/``expected_generation_sequence`` are the committed
    selection inputs the plan was drawn from, so a commit can reject a plan
    that no longer matches the state.
    """

    zone_key: str
    tick: int
    expected_seed: int | None
    expected_generation_sequence: int | None
    placements: tuple[PopulationPlacement, ...]
    blocked_reason: str | None

    @property
    def is_blocked(self) -> bool:
        return self.blocked_reason is not None


@dataclass(frozen=True, slots=True)
class PopulationPosition:
    """One actual wilderness coordinate (never a pooled room identity)."""

    wilderness: str
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class PopulationPresence:
    """One individual's complete presence fact at one game-time tick.

    A dead or absent individual carries ``alive=False`` and no position: a
    corpse or a removed row holds no birth headroom. ``home_zone`` and
    ``site_key`` stay the durable ownership markers of the individual even when
    it is no longer alive, so a historical projection can restore the home
    ceiling it consumed without resurrecting it.
    """

    alive: bool
    position: PopulationPosition | None
    home_zone: str | None
    site_key: str | None


@dataclass(frozen=True, slots=True)
class PopulationTransition:
    """One committed presence change, with the complete before/after facts.

    ``source_id`` identifies the owning operation (engagement, placement,
    operator mutation), so a committed replay of the same operation is
    deduplicated while it is still pending.
    """

    source_id: str
    individual_id: int
    occurred_tick: int
    before: PopulationPresence
    after: PopulationPresence


@dataclass(frozen=True, slots=True)
class PopulationProtection:
    """One encounter's closed or open protected cell interval.

    ``end_tick`` is ``None`` while the session is still active: an active
    encounter protects its cell from ``start_tick`` onwards until it clears.
    A closed interval is inclusive on both ends, so a wave due exactly at the
    terminal endpoint stays blocked and the next positive retry can use the
    cell once protection has been passed.
    """

    engagement_id: str
    cell: PopulationPosition
    start_tick: int
    end_tick: int | None


@dataclass(frozen=True, slots=True)
class PopulationTimeline:
    """The durable chronological presence evidence of one wilderness world."""

    settled_through_tick: int
    transitions: tuple[PopulationTransition, ...]
    protection: tuple[PopulationProtection, ...]


# ---------------------------------------------------------------------------
# Durable state
# ---------------------------------------------------------------------------


def _require_wilderness(wilderness: Any) -> Any:
    """Reject an absent world with its named refusal."""
    if wilderness is None:
        raise RegionalPopulationWorldUnavailable(WORLD_UNAVAILABLE)
    return wilderness


def current_population_tick() -> int:
    """The current game-time tick for population boundary events.

    Reads the existing clock without creating it (a world that was never
    advanced reports ``0``), so a placement or provisioning step never depends
    on -- or forces -- world-clock provisioning.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return 0 if clock is None else clock.tick


def _wilderness() -> Any | None:
    """The live wilderness script, or ``None`` before the world is provisioned.

    Discovered at call time (like the site owner): the owner's clock contract
    may be queried before ``sync_wilderness`` builds the world, and that must
    find no world rather than raise.
    """
    return WildernessScript.objects.filter(db_key=WILDERNESS_NAME).first()


def live_wilderness() -> Any | None:
    """The live wilderness script this owner reads, or ``None`` before it exists."""
    return _wilderness()


def mapped_population_cell(entity: Any) -> dict | None:
    """The exact wilderness cell an entity stands on, for a session record.

    ``None`` for a nonwilderness or unregistered entity. The value is the
    actual coordinate registration, never a pooled room identity, so a combat
    record protects the cell the fight really happened on.
    """
    wilderness = _wilderness()
    if wilderness is None or entity is None:
        return None
    coordinates = actual_cell(wilderness, entity)
    if coordinates is None:
        return None
    return {
        "wilderness": _wilderness_name(wilderness),
        "x": coordinates[0],
        "y": coordinates[1],
    }


def _zone(zone_key: str) -> EcologyZone:
    """The authored zone this key names, or its named refusal."""
    zone = ECOLOGY_ZONE_REGISTRY.get(zone_key)
    if zone is None:
        raise UnknownEcologyZone(f"{UNKNOWN_ZONE}: {zone_key!r}")
    return zone


def _require_int(value: object, what: str, minimum: int = 0) -> int:
    """Reject a non-integer (bools included) or out-of-range value."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what} must be an integer, got {value!r}")
    if value < minimum:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} must be at least {minimum}, got {value!r}"
        )
    return value


def _require_seed(value: object, what: str) -> int:
    """Reject a non-integer seed (bools included); any integer is a seed."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} must be an integer, got {value!r}"
        )
    return value


def _require_argument_int(value: object, what: str, minimum: int = 0) -> int:
    """Reject a bad argument integer (bools included), as a plain value error."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{what} must be an integer, got {value!r}")
    if value < minimum:
        raise ValueError(f"{what} must be at least {minimum}, got {value!r}")
    return value


def _state_map(wilderness: Any) -> dict[str, dict]:
    """The durable per-zone state map, copied out for a whole-value write.

    An absent Attribute is the only empty state. A present value that is not a
    mapping of zone keys to mappings is malformed and refuses: it is never
    normalized into "nothing was initialized", which would let a later
    initialization overwrite saved owner state.
    """
    raw = wilderness.db.regional_population
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {REGIONAL_POPULATION_ATTRIBUTE!r} is not a mapping"
        )
    states: dict[str, dict] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, Mapping):
            raise MalformedPopulationState(
                f"{MALFORMED_STATE}: zone record {key!r} is not a mapping"
            )
        states[key] = dict(value)
    return states


def _write_state(wilderness: Any, states: Mapping[str, Mapping]) -> None:
    """Persist the whole per-zone state map (Evennia saves a top-level write)."""
    wilderness.db.regional_population = {key: dict(value) for key, value in states.items()}


_SEED_ABSENT = object()


def _seed_attribute(wilderness: Any) -> object:
    """The raw saved seed value, or ``_SEED_ABSENT`` when it was never written.

    Absence and a present-but-unusable value are distinct answers: only an
    absent Attribute may receive the first write.
    """
    handler = wilderness.attributes
    if not handler.has(POPULATION_SEED_ATTRIBUTE):
        return _SEED_ABSENT
    return handler.get(POPULATION_SEED_ATTRIBUTE)


def read_population_seed(wilderness: Any) -> int:
    """The explicitly initialized shared world seed of this world.

    An absent or malformed seed is the named ``population_seed_uninitialized``
    refusal: nothing here invents a default, rerolls, or converts an older
    save. An incompatible development world needs an explicit GM repair.
    """
    _require_wilderness(wilderness)
    seed = _seed_attribute(wilderness)
    if seed is _SEED_ABSENT or isinstance(seed, bool) or not isinstance(seed, int):
        raise PopulationSeedUninitialized(f"{SEED_UNINITIALIZED}: {PERSISTED_SEED_HINT}")
    return seed


def initialize_population_seed(wilderness: Any, *, seed: int, tick: int) -> int:
    """Write the shared world seed once, or return the saved one unchanged.

    Provisioning calls this only for a genuinely new wilderness script. A
    repeated call never rerolls an existing seed, and a malformed saved value
    refuses instead of being replaced.
    """
    _require_wilderness(wilderness)
    _require_argument_int(tick, "tick")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    saved = _seed_attribute(wilderness)
    if saved is not _SEED_ABSENT:
        # An existing value is never replaced, however unusable it is: malformed
        # owner state needs an explicit repair, not an implicit reseed.
        if isinstance(saved, bool) or not isinstance(saved, int):
            raise PopulationSeedUninitialized(f"{SEED_UNINITIALIZED}: malformed saved seed")
        return saved
    wilderness.attributes.add(POPULATION_SEED_ATTRIBUTE, int(seed))
    if not wilderness.attributes.has(POPULATION_TIMELINE_ATTRIBUTE):
        # The explicit fresh provisioning operation is the only creator of the
        # empty timeline. It carries no ordinary births and no recovery state.
        _write_timeline(wilderness, PopulationTimeline(int(tick), (), ()))
    _emit(
        "monster_population_seed_initialized",
        {"seed": int(seed), "tick": int(tick)},
    )
    return int(seed)


def zone_state(wilderness: Any, zone_key: str) -> ZonePopulationState | None:
    """One zone's committed selection state, or ``None`` when uninitialized.

    A present record must be complete and must agree with the shared world
    seed; contradictory owner state refuses rather than being silently
    normalized.
    """
    _require_wilderness(wilderness)
    record = _state_map(wilderness).get(zone_key)
    if record is None:
        return None
    required = (
        "initialized",
        "seed",
        "generation_sequence",
        "recovery_due_tick",
        "settled_through_tick",
    )
    missing = [field for field in required if field not in record]
    if missing:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: zone {zone_key!r} record lacks {missing}"
        )
    if record.get("initialized") is not True:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: zone {zone_key!r} is not initialized")
    seed = _require_seed(record.get("seed"), "seed")
    sequence = _require_int(record.get("generation_sequence"), "generation_sequence")
    settled = _require_int(record.get("settled_through_tick"), "settled_through_tick")
    due = record.get("recovery_due_tick")
    if due is not None:
        due = _require_int(due, "recovery_due_tick")
    world_seed = read_population_seed(wilderness)
    if seed != world_seed:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: zone {zone_key!r} seed {seed} disagrees with the "
            f"saved world seed {world_seed}"
        )
    return ZonePopulationState(zone_key, seed, sequence, due, settled)


# ---------------------------------------------------------------------------
# Reading individuals
# ---------------------------------------------------------------------------


def _living_monsters() -> tuple[Monster, ...]:
    """Every living ``Monster`` in the game, in deterministic persistent-ID order.

    Enumerated globally on purpose: an ordinary home owner must be found even
    when it is unregistered, detached from any room, or standing in another
    zone. ``persisted_hp`` reads stored HP without materializing or ticking a
    gauge.
    """
    return tuple(
        sorted(
            (
                individual
                for individual in Monster.objects.all_family()
                if persisted_hp(individual) > 0
            ),
            key=lambda individual: individual.pk,
        )
    )


def _is_wilderness(wilderness: Any, candidate: Any) -> bool:
    """Whether ``candidate`` is that wilderness script instance (same record)."""
    if candidate is None:
        return False
    if candidate is wilderness:
        return True
    return getattr(candidate, "pk", None) is not None and getattr(candidate, "pk", None) == getattr(
        wilderness, "pk", None
    )


def actual_cell(wilderness: Any, entity: Any) -> tuple[int, int] | None:
    """Where one entity actually stands in this wilderness, or ``None``.

    The coordinate registration is authoritative and independent of room
    materialization (an inactive cell keeps its registration). Only an
    unregistered entity attached to *this* wilderness's own room falls back to
    the room's active coordinates, so another wilderness at the same numeric
    cell can never consume this zone's headroom.
    """
    registration = getattr(wilderness, "itemcoordinates", None)
    if registration is not None:
        registered = registration.get(entity)
        if registered is not None:
            return coordinate_pair(registered)
    location = getattr(entity, "location", None)
    if location is None or not _is_wilderness(wilderness, getattr(location, "wilderness", None)):
        return None
    return coordinate_pair(getattr(location, "coordinates", None))


def coordinate_pair(value: object) -> tuple[int, int] | None:
    """A coordinate pair, or ``None`` when the value is not one."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    x, y = value
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
        return None
    return (x, y)


def _published_geography() -> Any:
    """The published map world's geography (a composition-root prerequisite)."""
    from world.maps.geography import current as current_geography

    return current_geography()


def _region_cells(zone: EcologyZone) -> frozenset[tuple[int, int]]:
    """Every cell of the zone's rectangles classified into its parent region.

    Deliberately wider than the birth geometry: settlement-excluded and
    otherwise non-birth cells still hold individuals who count locally.
    """
    terrain = _published_geography().terrain
    cells: set[tuple[int, int]] = set()
    for x_min, x_max, y_min, y_max in zone.rectangles:
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if region_for_coordinates(terrain, x, y) == zone.region_key:
                    cells.add((x, y))
    return frozenset(cells)


def _birth_cells(zone: EcologyZone) -> tuple[tuple[int, int], ...]:
    """Every eligible ordinary birth cell of one zone (the published geometry)."""
    return eligible_birth_cells(
        zone,
        geography=_published_geography(),
        entries=WILDERNESS_ENTRY_REGISTRY,
        policies=SETTLEMENT_BIRTH_POLICY_REGISTRY,
    )


def _session_participant_ids() -> frozenset[int]:
    """The dbrefs referenced by any persisted active combat session.

    Gathers both sides: an active encounter protects the cell it stands on from
    receiving an automatic birth, and no birth ever touches a session. A record
    that cannot be parsed protects nothing by name and is reported, not
    repaired.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.combat_session.records import read_session

    participants: set[int] = set()
    for player in PlayerCharacter.objects.all_family():
        if player.db.active_combat is None:
            continue
        try:
            record = read_session(player)
        except Exception:  # observability: ignore R2: planning is a pure read that must emit nothing; an unparseable persisted session protects nothing by name, and the combat owner reports its own unreadable records
            continue
        if record is None:
            continue
        participants.update(record.player_ids)
        participants.update(record.enemy_ids)
    return frozenset(participants)


def _active_session_protection(wilderness: Any) -> tuple[PopulationProtection, ...]:
    """Every persisted active session's open cell protection (a pure read).

    The durable record's ``population_cell`` is the authoritative battlefield
    cell: it is independent of pooled-room reuse, and a record whose cell is
    absent or names another wilderness protects nothing here.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.combat_session.records import read_session

    name = _wilderness_name(wilderness)
    protections: list[PopulationProtection] = []
    for player in PlayerCharacter.objects.all_family():
        if player.db.active_combat is None:
            continue
        try:
            record = read_session(player)
        except Exception:  # observability: ignore R2: planning is a pure read that must emit nothing; an unparseable persisted session protects nothing by name, and the combat owner reports its own unreadable records
            continue
        if record is None:
            continue
        cell = _protection_cell(record.population_cell)
        if cell is None or cell[0] != name:
            continue
        protections.append(
            PopulationProtection(
                engagement_id=record.engagement_id or record.session_id,
                cell=PopulationPosition(*cell),
                start_tick=record.started_tick,
                end_tick=None,
            )
        )
    return tuple(protections)


def _protected_cells(
    wilderness: Any, at_tick: int | None = None
) -> frozenset[tuple[int, int]]:
    """Cells that hold no lawful birth space at the evaluated tick.

    Protection comes from the durable timeline (closed historical intervals)
    plus any currently active strict session (an open interval), never from a
    mutable room identity. The actual-state read additionally scans the
    participants' real coordinates, so a session this owner cannot attribute
    to a recorded cell still shields the cell its participants occupy.
    """
    tick = current_population_tick() if at_tick is None else at_tick
    timeline = read_population_timeline(wilderness) if population_provisioned(wilderness) else None
    intervals = (
        (() if timeline is None else timeline.protection)
        + _active_session_protection(wilderness)
    )
    cells: set[tuple[int, int]] = set()
    name = _wilderness_name(wilderness)
    for protection in intervals:
        if protection.cell.wilderness != name:
            continue
        if protection.start_tick > tick:
            continue
        if protection.end_tick is not None and protection.end_tick < tick:
            continue
        cells.add((protection.cell.x, protection.cell.y))
    if at_tick is not None:
        return frozenset(cells)
    participants = _session_participant_ids()
    if not participants:
        return frozenset(cells)
    for individual in _living_monsters():
        if individual.pk in participants:
            cell = actual_cell(wilderness, individual)
            if cell is not None:
                cells.add(cell)
    from typeclasses.characters import PlayerCharacter

    for player in PlayerCharacter.objects.all_family():
        if player.pk in participants:
            cell = actual_cell(wilderness, player)
            if cell is not None:
                cells.add(cell)
    return frozenset(cells)


def population_counts(
    wilderness: Any, zone_key: str, *, at_tick: int | None = None
) -> PopulationCounts:
    """The zone's local, home-owned and per-cell individual measures (pure read).

    ``at_tick`` projects the measures at that game-time tick: the actual living
    state is read first, then every still-pending transition committed later
    than the tick is reversed through its own complete ``before`` facts, so a
    deleted individual or a future arrival never borrows headroom it did not
    have at the evaluated tick. ``None`` means the actual current state.

    Creates nothing, moves nothing, deletes nothing, and emits no event: an
    unchanged read must leave no trace beyond its own return value.
    """
    _require_wilderness(wilderness)
    zone = _zone(zone_key)
    local_cells = _region_cells(zone)
    name = _wilderness_name(wilderness)
    home: set[int] = set()
    cells: dict[tuple[int, int], set[int]] = {}
    for individual_id, presence in presence_at(wilderness, at_tick=at_tick).items():
        if not presence.alive:
            continue
        if presence.home_zone == zone_key:
            home.add(individual_id)
        position = presence.position
        if position is None or position.wilderness != name:
            continue
        cell = (position.x, position.y)
        if cell in local_cells:
            cells.setdefault(cell, set()).add(individual_id)
    local = {pk for occupants in cells.values() for pk in occupants}
    return PopulationCounts(
        local_ids=frozenset(local),
        home_ids=frozenset(home),
        cell_ids=MappingProxyType(
            {cell: frozenset(occupants) for cell, occupants in cells.items()}
        ),
    )


def protected_cells(wilderness: Any, *, at_tick: int) -> frozenset[tuple[int, int]]:
    """Cells that hold no lawful birth space at ``at_tick`` (a pure read).

    The single protection decision every birth route shares: an explicit site
    or regional wave must not place individuals on a cell an encounter owned
    during the evaluated interval.
    """
    _require_wilderness(wilderness)
    _require_argument_int(at_tick, "at_tick")
    return _protected_cells(wilderness, at_tick=at_tick)


# ---------------------------------------------------------------------------
# Presence timeline
# ---------------------------------------------------------------------------


def _wilderness_name(wilderness: Any) -> str:
    """The stable wilderness identity a position records."""
    name = getattr(wilderness, "db_key", None)
    if not isinstance(name, str) or not name:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: wilderness has no stable key")
    return name


def population_provisioned(wilderness: Any) -> bool:
    """Whether this world carries an explicitly initialized population seed.

    The seed is the activation gate: a world provisioned before the population
    system existed has no seed, so no presence evidence is recorded and no
    lifecycle work runs there. A present but unusable seed is *not* "absent";
    it stays the named refusal every reader answers with.
    """
    if wilderness is None:
        return False
    saved = _seed_attribute(wilderness)
    return saved is not _SEED_ABSENT


def require_initialized_population(wilderness: Any) -> None:
    """Refuse a preexisting world that lacks the complete runtime state.

    Fresh provisioning initializes the shared seed and every authored zone.
    A world that already exists must carry exactly that state; missing,
    malformed or extra zone records are the named operator refusal, with no
    automatic filling, conversion or reset from old coordinate slots.
    """
    _require_wilderness(wilderness)
    if not population_provisioned(wilderness):
        raise PopulationStateUninitialized(
            f"{STATE_UNINITIALIZED}: no saved population state"
        )
    try:
        states = _state_map(wilderness)
    except MalformedPopulationState as error:
        raise PopulationStateUninitialized(
            f"{STATE_UNINITIALIZED}: {error}"
        ) from error
    missing = sorted(set(ECOLOGY_ZONE_REGISTRY) - set(states))
    extra = sorted(set(states) - set(ECOLOGY_ZONE_REGISTRY))
    if missing or extra:
        raise PopulationStateUninitialized(
            f"{STATE_UNINITIALIZED}: missing zones {missing!r}, "
            f"unknown zones {extra!r}"
        )
    for zone_key in sorted(states):
        try:
            zone_state(wilderness, zone_key)
        except MalformedPopulationState as error:
            raise PopulationStateUninitialized(
                f"{STATE_UNINITIALIZED}: {error}"
            ) from error


def _require_optional_name(value: object, what: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what} must be a string or None")
    return value


def _is_sequence(value: object) -> bool:
    """Whether ``value`` is a saved sequence (Evennia's wrapper included)."""
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _protection_cell(value: object) -> tuple[str, int, int] | None:
    """A recorded protected cell, or ``None`` when it is not one."""
    if not isinstance(value, Mapping):
        return None
    name = value.get("wilderness")
    x, y = value.get("x"), value.get("y")
    if not isinstance(name, str) or not name:
        return None
    if isinstance(x, bool) or not isinstance(x, int):
        return None
    if isinstance(y, bool) or not isinstance(y, int):
        return None
    return name, x, y


def _position_to_dict(position: PopulationPosition | None) -> dict | None:
    if position is None:
        return None
    return {"wilderness": position.wilderness, "x": position.x, "y": position.y}


def _presence_to_dict(presence: PopulationPresence) -> dict:
    return {
        "alive": presence.alive,
        "position": _position_to_dict(presence.position),
        "home_zone": presence.home_zone,
        "site_key": presence.site_key,
    }


def _presence_from_dict(value: object, what: str) -> PopulationPresence:
    if not isinstance(value, Mapping):
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what} is not a mapping")
    required = {"alive", "position", "home_zone", "site_key"}
    if set(value) != required:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} must carry exactly {sorted(required)}"
        )
    alive = value["alive"]
    if not isinstance(alive, bool):
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what}.alive must be a boolean")
    raw_position = value["position"]
    position = None
    if raw_position is not None:
        cell = _protection_cell(raw_position)
        if cell is None:
            raise MalformedPopulationState(
                f"{MALFORMED_STATE}: {what}.position is not a wilderness cell"
            )
        position = PopulationPosition(*cell)
    home_zone = _require_optional_name(value["home_zone"], f"{what}.home_zone")
    site_key = _require_optional_name(value["site_key"], f"{what}.site_key")
    if not alive and position is not None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} is absent but carries a position"
        )
    return PopulationPresence(alive, position, home_zone, site_key)


def _transition_to_dict(transition: PopulationTransition) -> dict:
    return {
        "source_id": transition.source_id,
        "individual_id": transition.individual_id,
        "occurred_tick": transition.occurred_tick,
        "before": _presence_to_dict(transition.before),
        "after": _presence_to_dict(transition.after),
    }


def _transition_from_dict(value: object, index: int) -> PopulationTransition:
    what = f"transition {index}"
    if not isinstance(value, Mapping):
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what} is not a mapping")
    source_id = value.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what}.source_id is empty")
    individual_id = _require_int(value.get("individual_id"), f"{what}.individual_id", 1)
    occurred_tick = _require_int(value.get("occurred_tick"), f"{what}.occurred_tick")
    return PopulationTransition(
        source_id=source_id,
        individual_id=individual_id,
        occurred_tick=occurred_tick,
        before=_presence_from_dict(value.get("before"), f"{what}.before"),
        after=_presence_from_dict(value.get("after"), f"{what}.after"),
    )


def _protection_to_dict(protection: PopulationProtection) -> dict:
    return {
        "engagement_id": protection.engagement_id,
        "cell": _position_to_dict(protection.cell),
        "start_tick": protection.start_tick,
        "end_tick": protection.end_tick,
    }


def _protection_from_dict(value: object, index: int) -> PopulationProtection:
    what = f"protection {index}"
    if not isinstance(value, Mapping):
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what} is not a mapping")
    required = {"engagement_id", "cell", "start_tick", "end_tick"}
    if set(value) != required:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} must carry exactly {sorted(required)}"
        )
    engagement_id = value["engagement_id"]
    if not isinstance(engagement_id, str) or not engagement_id:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what}.engagement_id is empty")
    cell = _protection_cell(value["cell"])
    if cell is None:
        raise MalformedPopulationState(f"{MALFORMED_STATE}: {what}.cell is not a cell")
    start_tick = _require_int(value["start_tick"], f"{what}.start_tick")
    raw_end = value["end_tick"]
    end_tick = None if raw_end is None else _require_int(raw_end, f"{what}.end_tick")
    if end_tick is not None and end_tick < start_tick:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {what} ends before it starts"
        )
    return PopulationProtection(engagement_id, PopulationPosition(*cell), start_tick, end_tick)


def read_population_timeline(wilderness: Any) -> PopulationTimeline:
    """The durable chronological presence evidence of this world.

    A missing or malformed timeline is the named owner-state refusal: it is
    never reconstructed from older records, and no implicit empty timeline is
    substituted for saved owner state. The explicit seed initialization is the
    only creator of the empty value.
    """
    _require_wilderness(wilderness)
    raw = wilderness.db.population_timeline
    if not isinstance(raw, Mapping):
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: {POPULATION_TIMELINE_ATTRIBUTE!r} is missing or not a mapping"
        )
    unknown = set(raw) - {"settled_through_tick", "transitions", "protection"}
    if unknown:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: timeline has unknown fields {sorted(unknown)}"
        )
    settled = _require_int(raw.get("settled_through_tick"), "settled_through_tick")
    transitions_raw = raw.get("transitions")
    protection_raw = raw.get("protection")
    if not _is_sequence(transitions_raw) or not _is_sequence(protection_raw):
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: timeline transitions/protection must be lists"
        )
    transitions = tuple(
        _transition_from_dict(value, index)
        for index, value in enumerate(transitions_raw)
    )
    protection = tuple(
        _protection_from_dict(value, index)
        for index, value in enumerate(protection_raw)
    )
    return PopulationTimeline(settled, transitions, protection)


def _write_timeline(wilderness: Any, timeline: PopulationTimeline) -> None:
    wilderness.db.population_timeline = {
        "settled_through_tick": timeline.settled_through_tick,
        "transitions": [_transition_to_dict(t) for t in timeline.transitions],
        "protection": [_protection_to_dict(p) for p in timeline.protection],
    }


def presence_of(
    wilderness: Any,
    individual: Any,
    *,
    alive: bool | None = None,
    cell: tuple[int, int] | None = None,
) -> PopulationPresence:
    """One individual's complete presence fact, read without writing.

    ``alive`` defaults to the stored HP; an explicit ``False`` describes the
    post-mutation absence and carries no position. ``cell`` lets a caller that
    already captured the pre-move registration describe that exact cell.
    """
    _require_wilderness(wilderness)
    living = persisted_hp(individual) > 0 if alive is None else bool(alive)
    position = None
    if living:
        coordinates = coordinate_pair(cell) if cell is not None else actual_cell(wilderness, individual)
        if coordinates is not None:
            position = PopulationPosition(
                _wilderness_name(wilderness), coordinates[0], coordinates[1]
            )
    return PopulationPresence(
        alive=living,
        position=position,
        home_zone=_require_optional_name(
            getattr(individual.db, "home_ecology_zone", None), "home_ecology_zone"
        ),
        site_key=_require_optional_name(
            getattr(individual.db, "site_key", None), "site_key"
        ),
    )


def record_population_transition(
    wilderness: Any, transition: PopulationTransition
) -> None:
    """Append one committed presence change to the durable timeline.

    The caller has already performed its own owner mutation inside its
    transaction; this records the complete before/after facts the chronological
    coordinator replays. A world without an explicit population seed records
    nothing (the population system is not provisioned there), while a
    provisioned world with a missing or malformed timeline refuses by name. A
    transition already pending with the same ``source_id`` and individual is a
    duplicate commit and is not appended twice.
    """
    _require_wilderness(wilderness)
    if not population_provisioned(wilderness):
        return
    if not isinstance(transition.source_id, str) or not transition.source_id:
        raise ValueError("source_id must be a non-empty string")
    _require_argument_int(transition.individual_id, "individual_id", 1)
    _require_argument_int(transition.occurred_tick, "occurred_tick")
    if not isinstance(transition.before, PopulationPresence) or not isinstance(
        transition.after, PopulationPresence
    ):
        raise ValueError("before and after must be PopulationPresence facts")
    timeline = read_population_timeline(wilderness)
    for pending in timeline.transitions:
        if (
            pending.source_id == transition.source_id
            and pending.individual_id == transition.individual_id
        ):
            return
    transitions = sorted(
        (*timeline.transitions, transition),
        key=lambda item: (item.occurred_tick, item.source_id, item.individual_id),
    )
    _write_timeline(
        wilderness,
        PopulationTimeline(timeline.settled_through_tick, tuple(transitions), timeline.protection),
    )


def record_population_protection(
    wilderness: Any,
    *,
    engagement_id: str,
    cell: tuple[int, int],
    start_tick: int,
    end_tick: int | None,
) -> None:
    """Copy one encounter's exact cell and interval into the durable timeline.

    A closed interval is recorded before the session clears, so a catch-up that
    later passes those ticks still refuses to birth into the historical
    battlefield. Repeated evidence for the same engagement and start is a
    duplicate commit and is not appended twice.
    """
    _require_wilderness(wilderness)
    if not population_provisioned(wilderness):
        return
    if not isinstance(engagement_id, str) or not engagement_id:
        raise ValueError("engagement_id must be a non-empty string")
    coordinates = coordinate_pair(cell)
    if coordinates is None:
        raise ValueError("cell must be one integer coordinate pair")
    _require_argument_int(start_tick, "start_tick")
    if end_tick is not None:
        _require_argument_int(end_tick, "end_tick", start_tick)
    position = PopulationPosition(
        _wilderness_name(wilderness), coordinates[0], coordinates[1]
    )
    timeline = read_population_timeline(wilderness)
    for pending in timeline.protection:
        if (
            pending.engagement_id == engagement_id
            and pending.start_tick == start_tick
        ):
            if pending.end_tick == end_tick:
                return
            # The open active record is replaced by its closed terminal
            # interval: the cell stays protected for the same start.
            remaining = tuple(
                item
                for item in timeline.protection
                if not (
                    item.engagement_id == engagement_id
                    and item.start_tick == start_tick
                )
            )
            _write_timeline(
                wilderness,
                PopulationTimeline(
                    timeline.settled_through_tick,
                    timeline.transitions,
                    (
                        *remaining,
                        PopulationProtection(
                            engagement_id, position, start_tick, end_tick
                        ),
                    ),
                ),
            )
            return
    _write_timeline(
        wilderness,
        PopulationTimeline(
            timeline.settled_through_tick,
            timeline.transitions,
            (
                *timeline.protection,
                PopulationProtection(engagement_id, position, start_tick, end_tick),
            ),
        ),
    )


def presence_at(
    wilderness: Any, *, at_tick: int | None = None
) -> dict[int, PopulationPresence]:
    """Every known individual's presence at one tick, keyed by persistent ID.

    The actual living state is the base; a pending transition committed later
    than ``at_tick`` is reversed through its complete before facts in reverse
    chronological, stable source/individual order. An individual whose row was
    deleted is restored only for accounting: nothing is recreated and no
    public presence is fabricated.
    """
    _require_wilderness(wilderness)
    name = _wilderness_name(wilderness)
    presence: dict[int, PopulationPresence] = {}
    for individual in _living_monsters():
        cell = actual_cell(wilderness, individual)
        presence[individual.pk] = PopulationPresence(
            True,
            None if cell is None else PopulationPosition(name, cell[0], cell[1]),
            _require_optional_name(
                getattr(individual.db, "home_ecology_zone", None), "home_ecology_zone"
            ),
            _require_optional_name(
                getattr(individual.db, "site_key", None), "site_key"
            ),
        )
    if at_tick is None:
        return presence
    _require_argument_int(at_tick, "at_tick")
    if not population_provisioned(wilderness):
        return presence
    timeline = read_population_timeline(wilderness)
    pending = [
        transition
        for transition in timeline.transitions
        if transition.occurred_tick > at_tick
    ]
    for transition in sorted(
        pending,
        key=lambda item: (item.occurred_tick, item.source_id, item.individual_id),
        reverse=True,
    ):
        presence[transition.individual_id] = transition.before
    return presence


def settle_timeline_through(
    wilderness: Any, tick: int, *, retain: frozenset[int] = frozenset()
) -> None:
    """Consume every fact at or before ``tick`` after its boundary was applied.

    Pending transitions are dropped only once the coordinator has settled their
    boundary, and a closed protection interval is retired only after progress
    has passed its inclusive end. ``retain`` names individuals whose latest
    loss is still owed to a deferred site clear: their evidence is not
    consumed until the site has used it. Repeating the same tick is a no-op.
    """
    _require_wilderness(wilderness)
    if not population_provisioned(wilderness):
        return
    _require_argument_int(tick, "tick")
    timeline = read_population_timeline(wilderness)
    if tick <= timeline.settled_through_tick:
        return
    _write_timeline(
        wilderness,
        PopulationTimeline(
            tick,
            tuple(
                t
                for t in timeline.transitions
                if t.occurred_tick > tick or t.individual_id in retain
            ),
            tuple(
                p for p in timeline.protection if p.end_tick is None or p.end_tick >= tick
            ),
        ),
    )


def _write_zone_fields(wilderness: Any, zone_key: str, **fields: object) -> None:
    """Update named fields of one existing zone record, preserving the rest."""
    states = _state_map(wilderness)
    record = dict(states[zone_key])
    record.update(fields)
    states[zone_key] = record
    _write_state(wilderness, states)


def initialized_zone_keys(wilderness: Any) -> tuple[str, ...]:
    """Every zone key with a committed record, in deterministic order."""
    _require_wilderness(wilderness)
    return tuple(sorted(_state_map(wilderness)))


def density_lower_bound(wilderness: Any, zone_key: str) -> int:
    """The zone's authored lower individual bound at its current geometry."""
    zone = _zone(zone_key)
    birth_cells = _birth_cells(zone)
    if not birth_cells:
        return 0
    lower, _upper = density_bounds(
        len(birth_cells), zone.lower_density, zone.upper_density
    )
    return lower


def note_population_boundary(wilderness: Any, zone_key: str, *, tick: int) -> None:
    """Establish or cancel a zone's recovery episode at one settled boundary.

    A first below-bound state schedules one delayed due time; further losses
    leave a pending due unchanged. Restored density (returning members, an
    explicit placement or a completed wave) cancels the episode without a
    birth, draw or generation-sequence change. This never waves: a due tick is
    settled by :func:`settle_recovery_due`.
    """
    _require_wilderness(wilderness)
    _require_argument_int(tick, "tick")
    state = zone_state(wilderness, zone_key)
    if state is None:
        return
    zone = _zone(zone_key)
    lower = density_lower_bound(wilderness, zone_key)
    below = len(population_counts(wilderness, zone_key, at_tick=tick).local_ids) < lower
    fields: dict[str, object] = {"settled_through_tick": max(state.settled_through_tick, tick)}
    if not below:
        if state.recovery_due_tick is not None:
            fields["recovery_due_tick"] = None
    elif state.recovery_due_tick is None:
        fields["recovery_due_tick"] = tick + zone.recovery_delay
    if fields != {
        "settled_through_tick": state.settled_through_tick,
        "recovery_due_tick": state.recovery_due_tick,
    }:
        _write_zone_fields(wilderness, zone_key, **fields)


def settle_recovery_due(
    wilderness: Any, zone_key: str, *, tick: int
) -> list[ScheduledEvent]:
    """Settle one due recovery episode: cancel, wave, or lawful blockage.

    The living population is recomputed first. At or above the lower bound the
    episode is cancelled with no birth, draw or sequence change. Otherwise one
    complete composition is committed inside every ceiling and the wave
    budget, then the remaining deficit schedules the next wave one positive
    replenishment interval later. Temporary blockage creates nothing, leaves
    the generation sequence untouched, emits one bounded reason event and
    retries at that same interval.
    """
    _require_wilderness(wilderness)
    _require_argument_int(tick, "tick")
    state = zone_state(wilderness, zone_key)
    if state is None:
        return []
    due = state.recovery_due_tick
    if due is None or due > tick:
        return []
    zone = _zone(zone_key)
    lower = density_lower_bound(wilderness, zone_key)
    if len(population_counts(wilderness, zone_key, at_tick=tick).local_ids) >= lower:
        _write_zone_fields(
            wilderness,
            zone_key,
            recovery_due_tick=None,
            settled_through_tick=max(state.settled_through_tick, tick),
        )
        return []
    plan = plan_population_wave(wilderness, zone_key, tick=tick)
    if plan.is_blocked:
        _write_zone_fields(
            wilderness,
            zone_key,
            recovery_due_tick=tick + zone.replenishment_interval,
            settled_through_tick=max(state.settled_through_tick, tick),
        )
        context = {
            "zone": zone_key,
            "tick": tick,
            "reason": plan.blocked_reason,
            "due_tick": tick + zone.replenishment_interval,
        }
        _emit("monster_population_recovery_blocked", context)
        return [ScheduledEvent("monster_population_recovery_blocked", tick, context)]
    created = commit_population_wave(wilderness, plan)
    still_below = (
        len(population_counts(wilderness, zone_key, at_tick=tick).local_ids) < lower
    )
    _write_zone_fields(
        wilderness,
        zone_key,
        recovery_due_tick=(
            tick + zone.replenishment_interval if still_below else None
        ),
    )
    context = {
        "zone": zone_key,
        "tick": tick,
        "created": len(created),
        "sequence": plan.expected_generation_sequence + 1,
        "due_tick": None if not still_below else tick + zone.replenishment_interval,
    }
    return [ScheduledEvent("monster_population_wave", tick, context)]


# ---------------------------------------------------------------------------
# Deterministic selection
# ---------------------------------------------------------------------------


def _draw(
    seed: int, stream_key: str, sequence: int, tick: int, ordinal: int, purpose: str
) -> Callable[[int], int]:
    """A rejection-sampling integer sampler bound to one draw purpose."""

    def sample(upper: int) -> int:
        if upper <= 0:
            raise ValueError("draw upper bound must be positive")
        limit = _DRAW_SPACE - (_DRAW_SPACE % upper)
        draw_ordinal = 0
        while True:
            payload = json.dumps(
                [seed, stream_key, sequence, tick, ordinal, purpose, draw_ordinal],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            value = int.from_bytes(
                hashlib.sha256(payload).digest()[:_DRAW_BYTES], "big"
            )
            if value < limit:
                return value % upper
            draw_ordinal += 1

    return sample


def _weighted_pick(sample, rows: list[tuple[int, Any]]) -> Any:
    """Pick one row by its positive authored weight, in the given row order."""
    total = sum(weight for weight, _row in rows)
    roll = sample(total)
    for weight, row in rows:
        if roll < weight:
            return row
        roll -= weight
    return rows[-1][1]


def _count_vectors(composition: EncounterComposition, budget: int) -> list[tuple[int, ...]]:
    """Every inclusive member-count vector whose total fits ``budget``.

    Enumerated in member order with ascending counts, pruning with the
    remaining members' minima and maxima, so a complete group is never split
    below a member's minimum and no vector exceeds the budget.
    """
    members = composition.members
    suffix_min = [0] * (len(members) + 1)
    suffix_max = [0] * (len(members) + 1)
    for index in range(len(members) - 1, -1, -1):
        suffix_min[index] = suffix_min[index + 1] + members[index].minimum
        suffix_max[index] = suffix_max[index + 1] + members[index].maximum
    vectors: list[tuple[int, ...]] = []
    prefix: list[int] = []

    def walk(index: int, remaining: int) -> None:
        if index == len(members):
            vectors.append(tuple(prefix))
            return
        low = members[index].minimum
        high = min(members[index].maximum, remaining - suffix_min[index + 1])
        for count in range(low, high + 1):
            prefix.append(count)
            walk(index + 1, remaining - count)
            prefix.pop()

    walk(0, budget)
    return vectors


def _fitting_rows(
    zone: EcologyZone, allowance: int
) -> list[tuple[int, EncounterComposition, list[tuple[int, ...]]]]:
    """Pooled compositions with at least one complete outcome inside a budget.

    Rows are ordered by composition key (the deterministic order the design
    requires); a pool row naming an unknown composition is a registry contract
    violation, so it refuses instead of being skipped.
    """
    rows: list[tuple[int, EncounterComposition, list[tuple[int, ...]]]] = []
    for weighted in sorted(zone.pool, key=lambda row: row.composition_key):
        composition = ENCOUNTER_COMPOSITION_REGISTRY.get(weighted.composition_key)
        if composition is None:
            raise MalformedPopulationState(
                f"{MALFORMED_STATE}: pool row {weighted.composition_key!r} names no composition"
            )
        vectors = _count_vectors(composition, allowance)
        if vectors:
            rows.append((weighted.weight, composition, vectors))
    return rows


def sample_composition_counts(
    composition_key: str,
    *,
    seed: int,
    stream_key: str,
    sequence: int,
    budget: int,
) -> tuple[tuple[str, int], ...]:
    """Select one complete count vector of a composition inside a budget.

    The pure occurrence sampler other explicit-placement owners share with the
    ordinary wave planner: the same inclusive member ranges, the same
    rejection-sampling stream, and no truncation below a member's minimum. An
    occurrence is identified by ``(seed, stream_key, sequence)`` alone, so the
    same saved occurrence selects the same complete group across restarts and
    retries. A composition that cannot fit the budget at all is a caller
    contract violation, not a temporary space refusal, and refuses by name.
    """
    composition = ENCOUNTER_COMPOSITION_REGISTRY.get(composition_key)
    if composition is None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: unknown composition {composition_key!r}"
        )
    vectors = _count_vectors(composition, budget)
    if not vectors:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: composition {composition_key!r} has no complete "
            f"outcome inside budget {budget}"
        )
    index = _draw(
        seed, stream_key, sequence, 0, 0, _PURPOSE_SITE_COUNTS
    )(len(vectors))
    return tuple(
        (member.variant_key, count)
        for member, count in zip(composition.members, vectors[index])
    )


def _blocked(zone_key: str, tick: int, state: ZonePopulationState | None, reason: str) -> PopulationWavePlan:
    return PopulationWavePlan(
        zone_key=zone_key,
        tick=tick,
        expected_seed=None if state is None else state.seed,
        expected_generation_sequence=None if state is None else state.generation_sequence,
        placements=(),
        blocked_reason=reason,
    )


def plan_population_wave(wilderness: Any, zone_key: str, *, tick: int) -> PopulationWavePlan:
    """Plan one deterministic birth wave for a zone (a pure read).

    A successful plan is exactly one complete composition that fits both
    individual ceilings, the zone's wave budget and the chosen cell's
    remaining capacity. A blocked plan names why no lawful complete birth
    exists right now; it writes nothing and never splits a group.
    """
    _require_wilderness(wilderness)
    zone = _zone(zone_key)
    state = zone_state(wilderness, zone_key)
    if state is None:
        return _blocked(zone_key, tick, None, BLOCKED_UNINITIALIZED)

    birth_cells = _birth_cells(zone)
    if not birth_cells:
        return _blocked(zone_key, tick, state, BLOCKED_NO_LEGAL_SPACE)
    lower, upper = density_bounds(
        len(birth_cells), zone.lower_density, zone.upper_density
    )
    counts = population_counts(wilderness, zone_key, at_tick=tick)
    if len(counts.local_ids) >= lower:
        return _blocked(zone_key, tick, state, BLOCKED_LOCAL_SATISFIED)
    if len(counts.home_ids) >= upper:
        return _blocked(zone_key, tick, state, BLOCKED_HOME_SATURATED)
    allowance = min(upper - len(counts.home_ids), upper - len(counts.local_ids), zone.wave_budget)
    if allowance <= 0:
        return _blocked(zone_key, tick, state, BLOCKED_NO_LEGAL_SPACE)

    rows = _fitting_rows(zone, allowance)
    if not rows:
        return _blocked(zone_key, tick, state, BLOCKED_NO_LEGAL_SPACE)
    smallest = min(
        sum(vector) for _weight, _composition, vectors in rows for vector in vectors
    )
    protected = _protected_cells(wilderness, at_tick=tick)
    available = tuple(
        cell
        for cell in birth_cells
        if cell not in protected
        and zone.cell_capacity - len(counts.cell_ids.get(cell, frozenset())) >= smallest
    )
    if not available:
        return _blocked(zone_key, tick, state, BLOCKED_NO_LEGAL_SPACE)

    ordinal = 0
    cell = available[
        _draw(state.seed, zone_key, state.generation_sequence, tick, ordinal, _PURPOSE_CELL)(
            len(available)
        )
    ]
    budget = min(
        allowance, zone.cell_capacity - len(counts.cell_ids.get(cell, frozenset()))
    )
    cell_rows: list[tuple[int, tuple[EncounterComposition, list[tuple[int, ...]]]]] = []
    for weight, composition, vectors in rows:
        fitting = [vector for vector in vectors if sum(vector) <= budget]
        if fitting:
            cell_rows.append((weight, (composition, fitting)))
    if not cell_rows:
        return _blocked(zone_key, tick, state, BLOCKED_NO_LEGAL_SPACE)
    composition, vectors = _weighted_pick(
        _draw(state.seed, zone_key, state.generation_sequence, tick, ordinal, _PURPOSE_COMPOSITION),
        cell_rows,
    )
    index = _draw(
        state.seed, zone_key, state.generation_sequence, tick, ordinal, _PURPOSE_COUNTS
    )(len(vectors))
    groups = tuple(
        (member.variant_key, count)
        for member, count in zip(composition.members, vectors[index])
    )
    return PopulationWavePlan(
        zone_key=zone_key,
        tick=tick,
        expected_seed=state.seed,
        expected_generation_sequence=state.generation_sequence,
        placements=(PopulationPlacement(cell=cell, groups=groups),),
        blocked_reason=None,
    )


# ---------------------------------------------------------------------------
# Atomic commit
# ---------------------------------------------------------------------------


def _attach(individual: Monster, room: Any) -> None:
    """Attach one registered individual to an already active wilderness room.

    The location assignment alone leaves the room's ``contents`` cache stale
    (the contrib's own ``move_obj`` has the same shape), and a later rollback
    must be able to clear exactly what this added, so the cache is updated in
    the same step.
    """
    individual.location = room
    room.contents_cache.add(individual)


def _emit(event: str, context: Mapping[str, object]) -> None:
    """Schedule one boundary event on the enclosing durable commit."""
    frozen = dict(context)
    transaction.on_commit(lambda: log_info(event, context=frozen))


def _wave_context(
    zone: EcologyZone,
    plan: PopulationWavePlan,
    created: list[Monster],
    placement: PopulationPlacement,
) -> dict[str, object]:
    """The bounded boundary context one committed wave carries."""
    return {
        "zone": zone.key,
        "region": zone.region_key,
        "individual": tuple(individual.pk for individual in created),
        "species": tuple(sorted({str(individual.species_key) for individual in created})),
        "variant": tuple(
            sorted({str(individual.variant_key) for individual in created})
        ),
        "cell": placement.cell,
        "tick": plan.tick,
        "created": len(created),
        "sequence": plan.expected_generation_sequence + 1,
    }


def commit_population_wave(wilderness: Any, plan: PopulationWavePlan) -> tuple[int, ...]:
    """Commit one planned wave atomically, or reject it as stale.

    The plan is re-derived from the committed state before any write, so a
    caller cannot commit a hand-built, stale, partial or over-cap group. A
    blocked plan is a lawful no-op: it creates nothing and does not advance the
    generation sequence.
    """
    _require_wilderness(wilderness)
    zone = _zone(plan.zone_key)
    state = zone_state(wilderness, plan.zone_key)
    if plan.is_blocked:
        return ()
    if (
        state is None
        or plan.expected_seed != state.seed
        or plan.expected_generation_sequence != state.generation_sequence
    ):
        raise PopulationPlanStale(f"{STALE_PLAN}: {plan.zone_key!r} state changed since planning")
    fresh = plan_population_wave(wilderness, plan.zone_key, tick=plan.tick)
    if fresh.is_blocked or fresh.placements != plan.placements:
        raise PopulationPlanStale(
            f"{STALE_PLAN}: {plan.zone_key!r} no longer commits the planned group"
        )

    placement = plan.placements[0]
    surfaces = snapshot_population_surfaces(wilderness)
    created: list[Monster] = []
    try:
        with transaction.atomic():
            for variant_key, count in placement.groups:
                species_key = variant_species_key(variant_key)
                for _ in range(count):
                    individual = construct_species_individual(species_key, variant_key)
                    individual.db.home_ecology_zone = zone.key
                    wilderness.db.itemcoordinates[individual] = placement.cell
                    room = (wilderness.db.rooms or {}).get(placement.cell)
                    if room is not None:
                        _attach(individual, room)
                    created.append(individual)
            states = _state_map(wilderness)
            record = dict(states[zone.key])
            record["generation_sequence"] = state.generation_sequence + 1
            record["settled_through_tick"] = max(state.settled_through_tick, plan.tick)
            states[zone.key] = record
            _write_state(wilderness, states)
            _emit("monster_population_wave", _wave_context(zone, plan, created, placement))
    except Exception:
        restore_population_surfaces(surfaces)
        raise
    return tuple(individual.pk for individual in created)


def initialize_zone(wilderness: Any, zone_key: str, *, seed: int, tick: int) -> tuple[int, ...]:
    """Initialize one zone once, through repeated constrained waves.

    Initialization is an explicit one-time owner operation: it writes the
    zone's selection state and the complete initial population in one
    transaction, stopping when the local band's lower bound is reached or no
    lawful complete birth remains. An already-initialized zone returns nothing
    and keeps its stored seed, sequence and individuals -- a restart, a source
    reread, or a room preparation never refills or rerolls it.
    """
    _require_wilderness(wilderness)
    zone = _zone(zone_key)
    _require_argument_int(tick, "tick")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    world_seed = read_population_seed(wilderness)
    if seed != world_seed:
        raise PopulationSeedMismatch(
            f"{SEED_MISMATCH}: requested {seed} but the saved world seed is {world_seed}"
        )
    if zone_state(wilderness, zone_key) is not None:
        return ()

    surfaces = snapshot_population_surfaces(wilderness)
    created: list[int] = []
    try:
        with transaction.atomic():
            states = _state_map(wilderness)
            states[zone_key] = {
                "initialized": True,
                "seed": world_seed,
                "generation_sequence": 0,
                "recovery_due_tick": None,
                "settled_through_tick": tick,
            }
            _write_state(wilderness, states)
            birth_cells = _birth_cells(zone)
            if not birth_cells:
                raise MalformedPopulationState(
                    f"{MALFORMED_STATE}: zone {zone_key!r} has no eligible birth cell"
                )
            _lower, upper = density_bounds(
                len(birth_cells), zone.lower_density, zone.upper_density
            )
            for _ in range(upper + 1):
                wave = plan_population_wave(wilderness, zone_key, tick=tick)
                if wave.is_blocked:
                    break
                created.extend(commit_population_wave(wilderness, wave))
            else:
                raise MalformedPopulationState(
                    f"{MALFORMED_STATE}: zone {zone_key!r} did not converge on initialization"
                )
            # An initialization blocked below the lower bound establishes its
            # first delayed episode here; a converged zone keeps no due time.
            if len(population_counts(wilderness, zone_key, at_tick=tick).local_ids) < _lower:
                _write_zone_fields(
                    wilderness,
                    zone_key,
                    recovery_due_tick=tick + zone.recovery_delay,
                )
    except Exception:
        restore_population_surfaces(surfaces)
        raise
    return tuple(created)


# ---------------------------------------------------------------------------
# Explicit placement registration
# ---------------------------------------------------------------------------


def wilderness_registration_target(room: Any) -> tuple[Any, tuple[int, int]] | None:
    """The wilderness and cell a destination room actually occupies.

    Returns ``None`` for a non-wilderness room (the ordinary placement path). A
    wilderness room whose active coordinates were lost is not a valid placement
    surface and refuses by name.
    """
    wilderness = getattr(room, "wilderness", None)
    if wilderness is None:
        return None
    cell = coordinate_pair(getattr(room, "coordinates", None))
    if cell is None:
        raise ExplicitPlacementRefused(
            f"{PLACEMENT_REFUSED}: room {room!r} has no active wilderness coordinates"
        )
    return wilderness, cell


def register_explicit_individual(
    wilderness: Any,
    individual: Any,
    coordinates: tuple[int, int],
    *,
    tick: int,
) -> None:
    """Register one explicitly placed individual on a valid wilderness surface.

    Records the actual object at its real coordinate and attaches it only to an
    already materialized room (never creating one). This is the placement
    registration other owners call for approved manual and quest placements: it
    deliberately does **not** stamp ordinary home ownership, does not apply
    automatic density or settlement birth exclusions, and does not reconstruct
    the individual's identity or profile. It joins the placing owner's own
    transaction; it opens none and compensates nothing by itself.
    """
    _require_wilderness(wilderness)
    cell = coordinate_pair(coordinates)
    if cell is None:
        raise ExplicitPlacementRefused(
            f"{PLACEMENT_REFUSED}: {coordinates!r} is not one integer cell pair"
        )
    if not isinstance(individual, Monster) or getattr(individual, "pk", None) is None:
        raise ExplicitPlacementRefused(
            f"{PLACEMENT_REFUSED}: {individual!r} is not a persisted Monster"
        )
    if not wilderness.is_valid_coordinates(cell):
        raise ExplicitPlacementRefused(
            f"{PLACEMENT_REFUSED}: {cell} is not a valid wilderness placement surface"
        )
    wilderness.db.itemcoordinates[individual] = cell
    room = (wilderness.db.rooms or {}).get(cell)
    if room is not None:
        _attach(individual, room)
    # The arrival is presence evidence, not only a coordinate write: a later
    # historical projection must know this individual did not stand here
    # before this tick, so an earlier wave cannot borrow its headroom.
    record_population_transition(
        wilderness,
        PopulationTransition(
            source_id=f"explicit:{cell[0]}:{cell[1]}:{individual.pk}",
            individual_id=individual.pk,
            occurred_tick=tick,
            before=PopulationPresence(False, None, None, None),
            after=presence_of(wilderness, individual, alive=True, cell=cell),
        ),
    )
    _emit(
        "monster_population_individual_registered",
        {
            "individual": individual.pk,
            "coordinate": cell,
            "species": getattr(individual, "species_key", None),
            "variant": getattr(individual, "variant_key", None),
            "tick": tick,
        },
    )


# ---------------------------------------------------------------------------
# Surfaces for a caller-owned rollback
# ---------------------------------------------------------------------------


def _db_safe_attribute_snapshot(obj: Any, key: str) -> tuple[bool, Any]:
    """Snapshot one attribute that may embed live database objects.

    ``itemcoordinates`` is keyed by live ``Monster`` instances, which a plain
    ``deepcopy`` cannot copy; the ``dbserialize`` round-trip is the established
    deepcopy for values that embed database objects (the same helper
    ``world/maps/monster_sites.py`` uses).
    """
    exists = obj.attributes.has(key)
    value = from_pickle(to_pickle(obj.attributes.get(key))) if exists else None
    return exists, value


def snapshot_population_surfaces(wilderness: Any) -> dict[int, SurfaceSnapshot]:
    """Snapshot the durable population surfaces one owner write may touch."""
    _require_wilderness(wilderness)
    return {
        id(wilderness): SurfaceSnapshot(
            attributes={
                (REGIONAL_POPULATION_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, REGIONAL_POPULATION_ATTRIBUTE
                ),
                (POPULATION_SEED_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, POPULATION_SEED_ATTRIBUTE
                ),
                (ITEMCOORDINATES_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, ITEMCOORDINATES_ATTRIBUTE
                ),
                (POPULATION_TIMELINE_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, POPULATION_TIMELINE_ATTRIBUTE
                ),
            }
        )
    }


def _restore_attribute(
    obj: Any, key: str, category: str | None, snapshot: tuple[bool, Any]
) -> None:
    """Restore one attribute directly, without a second deepcopy of its value.

    The snapshot already holds a database-safe copy, and a value embedding live
    objects cannot be copied again; ``attributes.add`` re-encodes natively.
    A failed restore degrades to a cache reset and is reported.
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
        except Exception:  # observability: ignore R2: cache invalidation is best-effort; the restore failure itself is logged below
            pass
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "regional_population_attribute", "obj": str(obj), "key": key},
        )


def restore_population_surfaces(snapshot: Mapping[int, SurfaceSnapshot]) -> None:
    """Restore the durable and live surfaces captured before an owner write.

    Run after the failed transaction has rolled back. Restores each snapshot
    attribute, then reconciles the engine caches through the shared seam rather
    than duplicating it: the orphan sweep evicts the rows this write removed --
    created individuals, or a freshly provisioned wilderness script -- and
    re-reads the contents cache of every room that had received one, because a
    room contents cache is not transaction-aware. Safe to call with an empty
    snapshot, and safe to call in addition to the clock's generic stage
    restore: both are idempotent restorations of the same values. An empty
    snapshot still evicts rolled-back instances, because the caller may have
    created them before it could snapshot anything.
    """
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB
    from world.rules.surfaces import flush_instance, flush_orphan_instances

    candidates = {
        id(instance): instance
        for instance in (*ObjectDB.get_all_cached_instances(), *ScriptDB.get_all_cached_instances())
    }
    for obj_id, surface in snapshot.items():
        obj = candidates.get(obj_id)
        if obj is None or getattr(obj, "_is_deleted", False):
            continue
        for (key, category), value in surface.attributes.items():
            _restore_attribute(obj, key, category, value)
    flush_orphan_instances()
    # The orphan sweep covers the objects this write created; the snapshot's own
    # object is evicted here when the rollback removed its row too.
    for obj_id in snapshot:
        obj = candidates.get(obj_id)
        if obj is None or getattr(obj, "_is_deleted", False):
            continue
        if not type(obj).objects.filter(pk=obj.pk).exists():
            flush_instance(obj)


def snapshot_regional_population_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """The clock advance-surface contract for this owner.

    A pure read in the clock's ``surfaces`` shape: it discovers the wilderness
    the way the owner's writes do and snapshots the population state, the world
    seed and the coordinate registry, or answers ``{}`` before the world
    exists. A caller-owned rollback restores through
    :func:`restore_population_surfaces` with this exact mapping, which also
    reconciles the room contents caches and rolled-back instances the generic
    clock restore cannot see.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return {}
    return snapshot_population_surfaces(wilderness)


__all__ = [
    "BLOCKED_HOME_SATURATED",
    "BLOCKED_LOCAL_SATISFIED",
    "BLOCKED_NO_LEGAL_SPACE",
    "BLOCKED_UNINITIALIZED",
    "ExplicitPlacementRefused",
    "HOME_ZONE_ATTRIBUTE",
    "INITIAL_POPULATION_SEED",
    "MalformedPopulationState",
    "POPULATION_SEED_ATTRIBUTE",
    "POPULATION_TIMELINE_ATTRIBUTE",
    "PopulationCounts",
    "PopulationPlacement",
    "PopulationPlanStale",
    "PopulationPosition",
    "PopulationPresence",
    "PopulationProtection",
    "PopulationSeedMismatch",
    "PopulationSeedUninitialized",
    "PopulationStateUninitialized",
    "PopulationTimeline",
    "PopulationTransition",
    "PopulationWavePlan",
    "REGIONAL_POPULATION_ATTRIBUTE",
    "RegionalPopulationError",
    "RegionalPopulationWorldUnavailable",
    "UnknownEcologyZone",
    "ZonePopulationState",
    "actual_cell",
    "commit_population_wave",
    "coordinate_pair",
    "current_population_tick",
    "density_lower_bound",
    "initialized_zone_keys",
    "initialize_population_seed",
    "initialize_zone",
    "live_wilderness",
    "mapped_population_cell",
    "note_population_boundary",
    "plan_population_wave",
    "population_provisioned",
    "population_counts",
    "presence_at",
    "presence_of",
    "protected_cells",
    "read_population_seed",
    "read_population_timeline",
    "record_population_protection",
    "record_population_transition",
    "register_explicit_individual",
    "require_initialized_population",
    "restore_population_surfaces",
    "sample_composition_counts",
    "settle_recovery_due",
    "settle_timeline_through",
    "snapshot_population_surfaces",
    "snapshot_regional_population_surfaces",
    "wilderness_registration_target",
    "zone_state",
]
