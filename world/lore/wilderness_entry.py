"""Wilderness entry registry: which grid-placed anchor owns which wilderness
footprint, and which face-gates of that footprint lead back to its grid rooms
(wilderness-anchor-footprint Model A).

Module-level registries are the source of truth (AGENTS.md); the DB mirror in
``world.lore.sync`` is a projection. All geometry helpers are pure and derived
from the authored mask — consumers never re-derive it.
"""

from collections.abc import Mapping
from dataclasses import dataclass

# Canonical wilderness directions, short form (matches the resolver's
# DIRECTION_DELTAS keys and the wilderness-gateway spec vocabulary).
CANONICAL_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")

# Unit deltas per short direction, identical to the provider's geometry so
# registry math and traversal math cannot drift.
DIRECTION_DELTAS: dict[str, tuple[int, int]] = {
    "n": (0, 1),
    "ne": (1, 1),
    "e": (1, 0),
    "se": (1, -1),
    "s": (0, -1),
    "sw": (-1, -1),
    "w": (-1, 0),
    "nw": (-1, 1),
}

# Provider rectangle bounds are authored here as the validation input; the
# provider itself owns the live constants (imported lazily by validation to
# keep lore free of world.maps at module scope).
_PROVIDER_MAX = 223

# Direction opposites (face = the footprint side a gate sits on).
OPPOSITE_DIRECTION = {
    "n": "s",
    "s": "n",
    "e": "w",
    "w": "e",
    "ne": "sw",
    "sw": "ne",
    "nw": "se",
    "se": "nw",
}


@dataclass(frozen=True)
class WildernessGate:
    """One face-gate of an anchor footprint.

    ``return_direction`` is named from the wilderness side: standing on the
    gate's exterior approach cell, the exit with that direction traverses to
    the grid room ``(grid_xy, z_map_key)``. The gate's face is the opposite
    direction (the footprint side it sits on).
    """

    return_direction: str
    grid_xy: tuple[int, int]
    z_map_key: str


@dataclass(frozen=True)
class WildernessEntryPoint:
    """One anchor's wilderness gateway: an authored footprint mask plus gates.

    ``shape`` is an ASCII mask of ``#`` (footprint cell) and ``.`` (outside);
    ``shape[0][0]`` corresponds to wilderness cell ``origin_xy``. Exactly one
    ``#`` encodes a point-shape anchor (cave semantics): no footprint, every
    direction at the anchor cell is a gateway to the single gate room, and
    ``approach_cell(gate)`` IS the anchor cell.

    ``anchor_key`` must exist in ``world.lore.anchor_placement.
    ANCHOR_PLACEMENT_REGISTRY``; ``validate_wilderness_entries`` enforces it
    at sync time, not the dataclass.
    """

    anchor_key: str
    shape: tuple[str, ...]
    origin_xy: tuple[int, int]
    gates: tuple[WildernessGate, ...]

    @property
    def footprint_cells(self) -> frozenset[tuple[int, int]]:
        """Every ``#`` mask cell in world coordinates (empty for point-shape)."""
        if self.is_point_shape:
            return frozenset()
        origin_x, origin_y = self.origin_xy
        return frozenset(
            (origin_x + col, origin_y + row)
            for row, line in enumerate(self.shape)
            for col, cell in enumerate(line)
            if cell == "#"
        )

    @property
    def hash_cell_count(self) -> int:
        """Number of ``#`` cells in the mask (1 marks the point-shape variant)."""
        return sum(line.count("#") for line in self.shape)

    @property
    def is_point_shape(self) -> bool:
        return self.hash_cell_count == 1

    @property
    def anchor_cell(self) -> tuple[int, int] | None:
        """Bounding-box midpoint of the ``#`` cells (Python floor division).

        ``None`` only for a mask with no ``#`` at all, which validation
        rejects; consumers may treat it as total for validated data.
        """
        cells = [
            (col, row)
            for row, line in enumerate(self.shape)
            for col, cell in enumerate(line)
            if cell == "#"
        ]
        if not cells:
            return None
        min_x = min(x for x, _ in cells)
        max_x = max(x for x, _ in cells)
        min_y = min(y for _, y in cells)
        max_y = max(y for _, y in cells)
        origin_x, origin_y = self.origin_xy
        return (origin_x + (min_x + max_x) // 2, origin_y + (min_y + max_y) // 2)

    def gate_for(self, return_direction: str) -> WildernessGate | None:
        """The gate entered from direction ``return_direction``, if authored."""
        for gate in self.gates:
            if gate.return_direction == return_direction:
                return gate
        return None

    def approach_cell(self, gate: WildernessGate) -> tuple[int, int] | None:
        """The exterior cell a wilderness traveler stands on to take ``gate``.

        Point-shape entries: the anchor cell itself (identity pinned by the
        wilderness-gateway registry requirement). Footprint entries: walk from
        ``anchor_cell`` along the face opposite ``gate.return_direction`` while
        inside the footprint; the first cell outside is the approach cell.
        ``None`` only for data validation rejects (missing anchor, gate whose
        ray never leaves the mask).
        """
        anchor = self.anchor_cell
        if anchor is None:
            return None
        if self.is_point_shape:
            return anchor
        face = OPPOSITE_DIRECTION.get(gate.return_direction)
        if face is None:
            return None
        dx, dy = DIRECTION_DELTAS[face]
        footprint = self.footprint_cells
        cell = anchor
        crossed = False
        # The walk is bounded by the provider rectangle: a footprint touching
        # a rect edge would otherwise ray forever through outside-rect cells
        # (validation rejects such gates explicitly).
        while cell in footprint and _in_provider_rect(cell):
            crossed = True
            cell = (cell[0] + dx, cell[1] + dy)
        if not crossed or not _in_provider_rect(cell):
            return None
        return cell


def _footprint_ray_crosses(entry: WildernessEntryPoint, gate: WildernessGate) -> bool:
    """Whether the gate's face ray starts inside the entry's footprint."""
    anchor = entry.anchor_cell
    return anchor is not None and anchor in entry.footprint_cells


def _iter_map_extents() -> dict[str, set[tuple[int, int]]]:
    """Prototype-coordinate extents per grid map key.

    Deferred import: lore must not import ``world.maps`` at module scope, and
    this is only consulted by the sync-time validation call (no import cycle —
    ``altoria_capital`` imports nothing from lore).
    """
    from world.maps.altoria_capital import XYMAP_DATA_LIST

    extents: dict[str, set[tuple[int, int]]] = {}
    for data in XYMAP_DATA_LIST:
        cells = {
            key
            for key in data["prototypes"]
            if isinstance(key, tuple) and len(key) == 2 and all(isinstance(v, int) for v in key)
        }
        extents[str(data["zcoord"])] = cells
    return extents


def _in_provider_rect(cell: tuple[int, int]) -> bool:
    x, y = cell
    return 0 <= x <= _PROVIDER_MAX and 0 <= y <= _PROVIDER_MAX


def validate_wilderness_entries(
    registry: Mapping[str, WildernessEntryPoint] | None = None,
) -> None:
    """Pure, DB-free validation of the whole authored registry (design D5).

    Raises ``ValueError`` naming the offending entry and the rejected rule.
    Called by ``world.lore.sync.sync_all()`` before mirroring so malformed
    authored data fails at startup.
    """
    if registry is None:
        registry = WILDERNESS_ENTRY_REGISTRY

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY

    def fail(anchor_key: str, rule: str) -> None:
        raise ValueError(f"WILDERNESS_ENTRY_REGISTRY[{anchor_key!r}]: {rule}")

    all_footprints: dict[str, frozenset[tuple[int, int]]] = {}
    for anchor_key, entry in registry.items():
        # -- anchor_key resolves against change 12's placement registry.
        if entry.anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            fail(anchor_key, f"anchor_key {entry.anchor_key!r} absent from ANCHOR_PLACEMENT_REGISTRY")

        # -- mask grammar: rectangle of '#'/'.' with at least one '#'.
        if not entry.shape:
            fail(anchor_key, "empty mask")
        row_length = len(entry.shape[0])
        if row_length == 0:
            fail(anchor_key, "empty mask row")
        for index, line in enumerate(entry.shape):
            if len(line) != row_length:
                fail(anchor_key, f"ragged mask: row {index} length {len(line)} != {row_length}")
            for char in line:
                if char not in "#.":
                    fail(anchor_key, f"illegal mask character {char!r}")
        if entry.hash_cell_count == 0:
            fail(anchor_key, "mask contains no '#' cell")

        # -- geometry: '#' cells inside the provider rectangle.
        origin_x, origin_y = entry.origin_xy
        for row, line in enumerate(entry.shape):
            for col, cell in enumerate(line):
                if cell == "#" and not _in_provider_rect(
                    (origin_x + col, origin_y + row)
                ):
                    fail(
                        anchor_key,
                        f"footprint cell ({origin_x + col}, {origin_y + row}) outside provider rectangle",
                    )

        footprint = entry.footprint_cells
        anchor = entry.anchor_cell
        if anchor is None:  # pragma: no cover - ruled out by no-'#' check
            fail(anchor_key, "anchor_cell is undefined")

        if not entry.is_point_shape:
            # -- footprint is 4-connected.
            start = next(iter(footprint))
            seen = {start}
            queue = [start]
            while queue:
                cx, cy = queue.pop()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nxt = (cx + dx, cy + dy)
                    if nxt in footprint and nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            if seen != footprint:
                fail(anchor_key, "footprint '#' cells are not 4-connected")
            # -- derived anchor cell is itself a '#' cell.
            if anchor not in footprint:
                fail(anchor_key, f"anchor_cell {anchor} is not a '#' footprint cell")
        all_footprints[anchor_key] = footprint

        # -- gates.
        if entry.is_point_shape:
            if len(entry.gates) != 1:
                fail(anchor_key, f"point-shape entry must have exactly one gate, found {len(entry.gates)}")
        directions: set[str] = set()
        for gate in entry.gates:
            if gate.return_direction not in CANONICAL_DIRECTIONS:
                fail(anchor_key, f"non-canonical return_direction {gate.return_direction!r}")
            if gate.return_direction in directions:
                fail(anchor_key, f"duplicated return_direction {gate.return_direction!r}")
            directions.add(gate.return_direction)
            if not entry.is_point_shape and not _footprint_ray_crosses(entry, gate):
                fail(
                    anchor_key,
                    f"gate {gate.return_direction!r} approach ray crosses no footprint cell",
                )

        # -- grid destination inside its map's extent.
        extents = None  # lazily loaded once per validated registry
        for gate in entry.gates:
            if extents is None:
                extents = _iter_map_extents()
            if gate.z_map_key not in extents:
                fail(anchor_key, f"gate {gate.return_direction!r}: unknown z_map_key {gate.z_map_key!r}")
            if gate.grid_xy not in extents[gate.z_map_key]:
                fail(
                    anchor_key,
                    f"gate {gate.return_direction!r}: grid_xy {gate.grid_xy} outside extent of {gate.z_map_key!r}",
                )

    # -- global cross-entry rules.
    def provider_valid_outside_footprints(cell: tuple[int, int]) -> bool:
        if not _in_provider_rect(cell):
            return False
        return not any(cell in other for other in all_footprints.values())

    seen_gate_keys: set[tuple[tuple[int, int], str]] = set()
    seen_gate_rooms: set[tuple[tuple[int, int], str]] = set()
    gate_rooms: list[tuple[str, WildernessGate]] = []
    for anchor_key, entry in registry.items():
        footprint = all_footprints[anchor_key]
        # -- two entries' footprints never overlap.
        for other_key, other_footprint in all_footprints.items():
            if other_key != anchor_key and footprint & other_footprint:
                fail(anchor_key, f"footprint overlaps {other_key!r}")
        # -- no footprint contains another entry's point-shape anchor cell.
        if not entry.is_point_shape:
            for other_key, other_entry in registry.items():
                if other_key != anchor_key and other_entry.is_point_shape:
                    other_anchor = other_entry.anchor_cell
                    if other_anchor is not None and other_anchor in footprint:
                        fail(anchor_key, f"footprint contains point anchor cell of {other_key!r}")
        for gate in entry.gates:
            approach = entry.approach_cell(gate)
            if approach is None:
                fail(
                    anchor_key,
                    f"gate {gate.return_direction!r} approach cell is undefined: its face ray "
                    "crosses no footprint cell or never lands inside the provider rectangle",
                )
            # -- two gates never share the same (approach_cell, return_direction).
            gate_key = (approach, gate.return_direction)
            if gate_key in seen_gate_keys:
                fail(anchor_key, f"gate {gate.return_direction!r} collides on (approach_cell, return_direction) {gate_key}")
            seen_gate_keys.add(gate_key)
            if not entry.is_point_shape:
                # -- no footprint contains another entry's gate approach cell
                #    (named before the generic provider-validity rule so the
                #    collision reports its precise cause).
                for other_key, other_footprint in all_footprints.items():
                    if other_key != anchor_key and approach in other_footprint:
                        fail(
                            anchor_key,
                            f"gate {gate.return_direction!r} approach cell {approach} lies inside footprint of {other_key!r}",
                        )
                # -- a footprint-entry approach cell is provider-valid and lies
                #    outside every footprint (its own ray rule already excludes
                #    its own footprint).
                if not provider_valid_outside_footprints(approach):
                    fail(
                        anchor_key,
                        f"gate {gate.return_direction!r} approach cell {approach} is not provider-valid outside every footprint",
                    )
            gate_rooms.append((anchor_key, gate))
        # -- a point anchor is never another entry's gate approach cell.
        if entry.is_point_shape and entry.anchor_cell is not None:
            for other_key, other_entry in registry.items():
                if other_key == anchor_key:
                    continue
                for other_gate in other_entry.gates:
                    if other_entry.approach_cell(other_gate) == entry.anchor_cell:
                        fail(
                            anchor_key,
                            f"point anchor cell is {other_key!r} gate {other_gate.return_direction!r} approach cell",
                        )
        # -- a point anchor advertises gateways in all eight directions; every
        #    neighbor must be provider-valid.
        if entry.is_point_shape and entry.anchor_cell is not None:
            for dx, dy in DIRECTION_DELTAS.values():
                neighbor = (entry.anchor_cell[0] + dx, entry.anchor_cell[1] + dy)
                if not provider_valid_outside_footprints(neighbor):
                    fail(
                        anchor_key,
                        f"point anchor {entry.anchor_cell} has provider-invalid neighbor {neighbor}",
                    )

    # -- one grid room hosts one gate: two gates sharing a destination room
    #    would collide on the room's single WildernessGateExit slot and leave
    #    one gate unprovisionable. Checked after the per-entry rules so every
    #    more precise collision rule keeps naming its own cause.
    for anchor_key, gate in gate_rooms:
        gate_room = (gate.grid_xy, gate.z_map_key)
        if gate_room in seen_gate_rooms:
            fail(anchor_key, f"gate {gate.return_direction!r} shares destination room {gate_room} with another gate")
        seen_gate_rooms.add(gate_room)


WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint] = {
    "capital_altoria": WildernessEntryPoint(
        anchor_key="capital_altoria",
        shape=("#####", "#####", "#####", "#####", "#####"),
        origin_xy=(58, 98),
        gates=(
            # 南門: a traveler at (60, 97) heading north enters the city.
            WildernessGate("n", (2, 0), "capital_altoria"),
            # 北門: a traveler at (60, 103) heading south enters the city.
            WildernessGate("s", (2, 4), "capital_altoria"),
        ),
    ),
}
