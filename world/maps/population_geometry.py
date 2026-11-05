"""Pure candidate-world birth geometry for the authored ecology zones.

An ordinary monster birth may only happen on a cell that is inside one authored
:class:`~world.lore.monster_placement.EcologyZone`, classified into that zone's
parent region, valid wilderness ground under the shared map rule, and outside
every inhabited settlement's birth-exclusion buffer. This module answers that
question from one explicit candidate world -- the geometry and the composed
wilderness entries handed in by the caller -- so publication never validates
against the previously published world, and birth geometry is independent of
which rooms happen to be materialized.

Nothing here reads a database, a live registry, or Evennia. The functions are
the shared mechanism the map composition root validates at publication; the
population owner will call :func:`eligible_birth_cells` with the world it is
already operating on.

Settlement exclusion uses the authored anchor category, never a display name:
an inhabited settlement (capital, city, town, port, or elven village) excludes
at least its immediate neighbouring cells, measured as the minimum Chebyshev
distance to the settlement's complete published footprint, or to its published
anchor cell when the settlement is a point shape. A dungeon entrance gets no
automatic buffer. An explicit :class:`SettlementBirthPolicy` row may only
enlarge an inhabited settlement's buffer; it can never introduce a nonsettlement
exclusion or shrink the generic one-cell ring.

Explicit manual and quest placement does not use this module: the design keeps
those exceptions outside automatic birth geometry, density and its exclusions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from elosern_map_core.terrain import is_valid_wilderness_cell, region_for_coordinates

from world.lore.anchors import AnchorKind
from world.lore.monster_placement import (
    EcologyZone,
    EncounterComposition,
    SettlementBirthPolicy,
    composition_bounds,
)

#: The authored anchor categories that are inhabited settlements. They receive
#: the automatic birth exclusion; every other category (a dungeon entrance in
#: particular) does not.
INHABITED_SETTLEMENT_KINDS: frozenset[AnchorKind] = frozenset(
    {
        AnchorKind.CAPITAL,
        AnchorKind.CITY,
        AnchorKind.TOWN,
        AnchorKind.PORT,
        AnchorKind.ELVEN_VILLAGE,
    }
)

#: The generic exclusion ring every inhabited settlement receives, in
#: Chebyshev cells. It excludes the footprint's complete exterior neighbour
#: ring; an authored policy row may only enlarge it.
MINIMUM_SETTLEMENT_BUFFER = 1


class PopulationGeometryError(ValueError):
    """A zone's birth geometry or its density interval is not usable."""


def _require_int(value: object, what: str, minimum: int) -> None:
    """Reject a non-integer (bools included) or out-of-range geometry value."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise PopulationGeometryError(
            f"{what} must be an integer literal, got {value!r}"
        )
    if value < minimum:
        raise PopulationGeometryError(f"{what} must be at least {minimum}, got {value!r}")


def density_bounds(
    eligible_count: int, lower_density: int, upper_density: int
) -> tuple[int, int]:
    """The usable individual bounds of one enabled zone, in integer arithmetic.

    ``lower_density`` and ``upper_density`` are individuals per one hundred
    eligible birth cells. The lower bound rounds the product up and the upper
    bound rounds it down, so a zone never promises an interval its cells cannot
    hold. An enabled zone must keep a positive usable interval: zero cells,
    densities outside ``0 < lower <= upper < 100``, and a rounding result with
    no positive band all reject before publication.
    """
    _require_int(eligible_count, "eligible birth-cell count", 1)
    _require_int(lower_density, "lower density", 0)
    _require_int(upper_density, "upper density", 0)
    if not 0 < lower_density <= upper_density < 100:
        raise PopulationGeometryError(
            "density values must satisfy 0 < lower <= upper < 100 individuals per "
            f"hundred eligible cells, got {lower_density!r}/{upper_density!r}"
        )
    lower = (eligible_count * lower_density + 99) // 100
    upper = (eligible_count * upper_density) // 100
    if lower < 1 or lower > upper:
        raise PopulationGeometryError(
            f"{eligible_count} eligible birth cells at densities "
            f"{lower_density}/{upper_density} per hundred yield no positive usable "
            f"individual interval ({lower}..{upper})"
        )
    return lower, upper


def _settlement_sources(
    geography: Any, entries: Mapping[str, Any]
) -> dict[str, tuple[tuple[int, int], ...]]:
    """Every inhabited settlement's complete published distance source.

    A footprint settlement measures distance from all of its masked cells; a
    point-shaped (or map-less) settlement uses its published anchor cell. Only
    inhabited categories appear, so a dungeon entrance can never become an
    automatic birth exclusion.

    An inhabited anchor that publishes no geometry at all contributes no
    exclusion: a settlement with no ground in this world has no surroundings to
    keep free. The authored composition root already refuses a location without
    a cell before publication, so this only describes a hand-built world (the
    managed-browser kit merges its stand-in anchors into the authored one).
    """
    sources: dict[str, tuple[tuple[int, int], ...]] = {}
    for anchor_key, anchor in geography.anchors.items():
        if anchor.kind not in INHABITED_SETTLEMENT_KINDS:
            continue
        entry = entries.get(anchor_key)
        if entry is not None and not entry.is_point_shape:
            sources[anchor_key] = tuple(sorted(entry.footprint_cells))
            continue
        published = geography.anchor_geography.get(anchor_key)
        cell = published.cell if published is not None else None
        if cell is None and entry is not None:
            cell = entry.anchor_cell
        if cell is None:
            continue
        sources[anchor_key] = (tuple(cell),)
    return sources


def _buffers(
    sources: Mapping[str, tuple[tuple[int, int], ...]],
    policies: Mapping[str, SettlementBirthPolicy],
) -> dict[str, int]:
    """Each inhabited settlement's effective buffer, never below the generic one."""
    for anchor_key, policy in policies.items():
        if anchor_key not in sources:
            raise PopulationGeometryError(
                f"settlement birth policy {anchor_key!r} names no inhabited "
                "settlement with published geometry"
            )
        _require_int(
            policy.buffer_cells,
            f"settlement birth policy {anchor_key!r} buffer cells",
            MINIMUM_SETTLEMENT_BUFFER,
        )
    return {
        anchor_key: max(
            MINIMUM_SETTLEMENT_BUFFER,
            policies[anchor_key].buffer_cells if anchor_key in policies else 0,
        )
        for anchor_key in sources
    }


def _chebyshev(first: tuple[int, int], second: tuple[int, int]) -> int:
    return max(abs(first[0] - second[0]), abs(first[1] - second[1]))


def _excluded(
    cell: tuple[int, int],
    sources: Mapping[str, tuple[tuple[int, int], ...]],
    buffers: Mapping[str, int],
) -> bool:
    """Whether ``cell`` lies inside any inhabited settlement's buffer."""
    for anchor_key, cells in sources.items():
        buffer = buffers[anchor_key]
        if any(_chebyshev(cell, source) <= buffer for source in cells):
            return True
    return False


def eligible_birth_cells(
    zone: EcologyZone,
    *,
    geography: Any,
    entries: Mapping[str, Any],
    policies: Mapping[str, SettlementBirthPolicy],
) -> tuple[tuple[int, int], ...]:
    """Every ordinary birth cell of ``zone`` in one candidate world.

    ``geography`` is the candidate geography snapshot (its terrain, anchors and
    published anchor cells) and ``entries`` the candidate world's composed
    wilderness entries. Rectangles are intersected with the parent region's
    classification and the shared wilderness-validity rule (which already
    rejects anchor footprint cells), then every inhabited settlement buffer is
    removed. Intersecting rectangles are deduplicated. Cells outside the zone's
    rectangles are simply absent: unconfigured ground has no implicit source.
    """
    terrain = geography.terrain
    footprints = frozenset().union(
        *(entry.footprint_cells for entry in entries.values())
    )
    sources = _settlement_sources(geography, entries)
    buffers = _buffers(sources, policies)
    cells: set[tuple[int, int]] = set()
    for x_min, x_max, y_min, y_max in zone.rectangles:
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                cell = (x, y)
                if cell in cells:
                    continue
                if region_for_coordinates(terrain, x, y) != zone.region_key:
                    continue
                if not is_valid_wilderness_cell(terrain, footprints, cell):
                    continue
                if _excluded(cell, sources, buffers):
                    continue
                cells.add(cell)
    return tuple(sorted(cells))


def _rectangle_cells(
    rectangle: tuple[int, int, int, int],
) -> Iterable[tuple[int, int]]:
    x_min, x_max, y_min, y_max = rectangle
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            yield (x, y)


def _recovery_problems(
    zone: EcologyZone,
    compositions: Mapping[str, EncounterComposition],
    lower: int,
    upper: int,
) -> list[str]:
    """Prove one complete composition can recover every unobstructed sub-lower zone.

    The proof is a bounded dynamic program over reachable population totals up
    to the upper bound. One composition is one wave step: its declared member
    ranges make every total between its minimum and maximum achievable, and a
    complete composition already fits the cell capacity and wave budget, so a
    single composition is always a legal wave. A wave may never truncate a
    member group below its minimum, and recovery never requires an exact lower
    population -- reaching or passing ``lower`` ends the episode. If any
    unobstructed start below the lower bound cannot reach the band inside the
    upper bound, the pool is an authoring error rather than a runtime retry.
    """
    problems: list[str] = []
    sizes: set[int] = set()
    for row in zone.pool:
        composition = compositions.get(row.composition_key)
        if composition is None:
            problems.append(
                f"ecology zone {zone.key!r} references unknown composition "
                f"{row.composition_key!r}"
            )
            continue
        smallest, largest = composition_bounds(composition)
        if largest > zone.cell_capacity:
            problems.append(
                f"ecology zone {zone.key!r} composition {row.composition_key!r} "
                f"can place {largest} individuals, above its cell capacity "
                f"{zone.cell_capacity}"
            )
        if largest > zone.wave_budget:
            problems.append(
                f"ecology zone {zone.key!r} composition {row.composition_key!r} "
                f"can place {largest} individuals, above its wave budget "
                f"{zone.wave_budget}"
            )
        if largest > upper:
            problems.append(
                f"ecology zone {zone.key!r} composition {row.composition_key!r} "
                f"can place {largest} individuals, above its upper bound {upper}"
            )
        sizes.update(range(smallest, largest + 1))
    if problems or not sizes:
        return problems

    reachable = [False] * (upper + 1)
    reachable[0] = True
    for total in range(upper + 1):
        if not reachable[total]:
            continue
        for size in sizes:
            if total + size <= upper:
                reachable[total + size] = True
    for start in range(lower):
        if any(reachable[target - start] for target in range(lower, upper + 1)):
            continue
        problems.append(
            f"ecology zone {zone.key!r} has no complete recovery path from "
            f"{start} living individuals to its lower bound {lower} within its "
            f"upper bound {upper}"
        )
        break
    return problems


def validate_ecology_geometry(
    *,
    geography: Any,
    entries: Mapping[str, Any],
    zones: Mapping[str, EcologyZone],
    compositions: Mapping[str, EncounterComposition],
    policies: Mapping[str, SettlementBirthPolicy],
) -> tuple[str, ...]:
    """Every candidate-world ecology defect, in deterministic zone-key order.

    The map composition root runs this against the candidate geography and the
    candidate world's own wilderness entries before publishing either, so a
    rejection leaves the previously published snapshot entirely untouched. It
    reports (never raises) so a candidate can name every defect at once; the
    caller collects these messages with its other join problems.
    """
    problems: list[str] = []
    terrain = geography.terrain
    regions = set(geography.regions)

    inhabited = {
        anchor_key
        for anchor_key, anchor in geography.anchors.items()
        if anchor.kind in INHABITED_SETTLEMENT_KINDS
    }
    for anchor_key, policy in sorted(policies.items()):
        if anchor_key not in geography.anchors:
            problems.append(
                f"settlement birth policy {anchor_key!r} names no known anchor"
            )
            continue
        if anchor_key not in inhabited:
            kind = geography.anchors[anchor_key].kind
            problems.append(
                f"settlement birth policy {anchor_key!r} names a "
                f"{getattr(kind, 'value', kind)!r} anchor, which is not an "
                "inhabited settlement"
            )
            continue
        if (
            isinstance(policy.buffer_cells, bool)
            or not isinstance(policy.buffer_cells, int)
            or policy.buffer_cells < MINIMUM_SETTLEMENT_BUFFER
        ):
            problems.append(
                f"settlement birth policy {anchor_key!r} buffer cells must be an "
                f"integer at least {MINIMUM_SETTLEMENT_BUFFER}, got "
                f"{policy.buffer_cells!r}"
            )

    owners: dict[tuple[int, int], str] = {}
    for zone_key, zone in sorted(zones.items()):
        if zone.region_key not in regions:
            problems.append(
                f"ecology zone {zone_key!r} names unknown terrain region "
                f"{zone.region_key!r}"
            )
            continue
        parent_cells = {
            cell
            for rectangle in zone.rectangles
            for cell in _rectangle_cells(rectangle)
            if region_for_coordinates(terrain, *cell) == zone.region_key
        }
        if not parent_cells:
            problems.append(
                f"ecology zone {zone_key!r} covers no cell of its parent region "
                f"{zone.region_key!r}"
            )
        shared = sorted(cell for cell in parent_cells if cell in owners)
        if shared:
            problems.append(
                f"ecology zone {zone_key!r} shares parent-region cell {shared[0]} "
                f"with ecology zone {owners[shared[0]]!r}"
            )
        for cell in parent_cells:
            owners.setdefault(cell, zone_key)

        try:
            eligible = eligible_birth_cells(
                zone, geography=geography, entries=entries, policies=policies
            )
        except PopulationGeometryError as error:
            problems.append(f"ecology zone {zone_key!r}: {error}")
            continue
        if not eligible:
            problems.append(
                f"ecology zone {zone_key!r} has no eligible birth cell after "
                "parent-region, validity and settlement exclusions"
            )
            continue
        try:
            lower, upper = density_bounds(
                len(eligible), zone.lower_density, zone.upper_density
            )
        except PopulationGeometryError as error:
            problems.append(f"ecology zone {zone_key!r}: {error}")
            continue
        problems.extend(_recovery_problems(zone, compositions, lower, upper))
    return tuple(problems)


__all__ = [
    "INHABITED_SETTLEMENT_KINDS",
    "MINIMUM_SETTLEMENT_BUFFER",
    "PopulationGeometryError",
    "density_bounds",
    "eligible_birth_cells",
    "validate_ecology_geometry",
]
