"""Wilderness entry registry: which grid-placed anchor owns which wilderness
footprint, and which face-gates of that footprint lead back to its grid rooms
(wilderness-anchor-footprint Model A).

Module-level registries are the source of truth (AGENTS.md); the DB mirror in
``world.lore.sync`` is a projection. All geometry helpers are pure and derived
from the authored mask — consumers never re-derive it.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import ReferenceError, settlement_node_ref, settlement_position

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

# The provider owns the live frame bounds. They are imported lazily at call
# time (module scope would be a lore -> world.maps import cycle), so the
# authoring contract can never drift from the runtime frame it validates.
def _provider_bounds() -> tuple[int, int]:
    from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

    return WILDERNESS_MAX_X, WILDERNESS_MAX_Y

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
    the authored settlement node ``destination``. The gate's face is the
    opposite direction (the footprint side it sits on). The destination room's
    current address is derived from the settlement graph at the consumer
    boundary; it is never stored here.
    """

    return_direction: str
    destination: QualifiedRef

    @property
    def z_map_key(self) -> str:
        """The map coordinate space of the destination identity."""

        return self.destination.map_id or ""


@dataclass(frozen=True)
class WildernessEntryPoint:
    """One anchor's wilderness gateway: an authored footprint mask plus gates.

    ``shape`` is an ASCII mask of ``#`` (footprint cell) and ``.`` (outside);
    ``shape[0][0]`` corresponds to wilderness cell ``origin_xy``. Exactly one
    ``#`` encodes a point-shape anchor (concealed cave/path semantics): no
    footprint, ``approach_cell(gate)`` IS the anchor cell, and only the gate's
    authored ``return_direction`` is a gateway. Every other direction at the
    anchor cell is an ordinary terrain-validity wilderness step, so a concealed
    entry never hijacks an unrelated route.

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
    the shared ``world.maps.map_data`` assembly imports nothing from lore).
    The assembly is the single home of the sparse settlement graphs
    (settlement-shops design §6.2 / §10; implement-sparse-settlement-graphs):
    validation must see every map a gate names or a second settlement's gate
    fails startup with ``unknown z_map_key``.
    """
    from world.maps.map_data import SETTLEMENT_GRAPHS

    return {
        map_id: {node.coordinate for node in graph.nodes.values()}
        for map_id, graph in SETTLEMENT_GRAPHS.items()
    }


def _in_provider_rect(cell: tuple[int, int]) -> bool:
    max_x, max_y = _provider_bounds()
    x, y = cell
    return 0 <= x <= max_x and 0 <= y <= max_y


def _is_walkable_terrain(cell: tuple[int, int]) -> bool:
    """Whether ``cell`` is land-side passable ground (the provider's rule).

    Deferred import for the same lore/world.maps boundary reason as
    :func:`_iter_map_extents`: the provider is the single owner of the terrain
    model, and validation must never keep a second copy of it.
    """
    from world.maps.wilderness_provider import is_walkable_cell

    return is_walkable_cell(cell)


def validate_wilderness_entries(
    registry: Mapping[str, WildernessEntryPoint] | None = None,
    *,
    index=None,
) -> None:
    """Pure, DB-free validation of the whole authored registry (design D5).

    Raises ``ValueError`` naming the offending entry and the rejected rule.
    Called by ``world.lore.sync.sync_all()`` before mirroring so malformed
    authored data fails at startup. ``index`` is the current settlement-node
    binding snapshot; production builds it from the live graphs, while a
    synthetic candidate passes its own so validation never reads a partially
    assembled registry.
    """
    if registry is None:
        registry = WILDERNESS_ENTRY_REGISTRY

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.maps.static_references import settlement_reference_index

    if index is None:
        index = settlement_reference_index()

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
                if cell == "#" and not _is_walkable_terrain(
                    (origin_x + col, origin_y + row)
                ):
                    fail(
                        anchor_key,
                        f"footprint cell ({origin_x + col}, {origin_y + row}) is not walkable terrain",
                    )

        footprint = entry.footprint_cells
        anchor = entry.anchor_cell
        if anchor is None:  # pragma: no cover - ruled out by no-'#' check
            fail(anchor_key, "anchor_cell is undefined")
        if not _is_walkable_terrain(anchor):
            fail(anchor_key, f"anchor_cell {anchor} is not walkable terrain")

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

        # -- grid destination resolves to an authored node inside its map's
        #    extent.
        extents = None  # lazily loaded once per validated registry
        for gate in entry.gates:
            if extents is None:
                extents = _iter_map_extents()
            try:
                position = settlement_position(
                    index,
                    gate.destination,
                    source=f"gate {gate.return_direction!r}",
                )
            except ReferenceError as error:
                fail(anchor_key, str(error))
            if gate.z_map_key not in extents:
                fail(anchor_key, f"gate {gate.return_direction!r}: unknown z_map_key {gate.z_map_key!r}")
            if position not in extents[gate.z_map_key]:
                fail(
                    anchor_key,
                    f"gate {gate.return_direction!r}: destination {position} outside extent of {gate.z_map_key!r}",
                )

    # -- global cross-entry rules.
    def provider_valid_outside_footprints(cell: tuple[int, int]) -> bool:
        if not _in_provider_rect(cell) or not _is_walkable_terrain(cell):
            return False
        return not any(cell in other for other in all_footprints.values())

    seen_gate_keys: set[tuple[tuple[int, int], str]] = set()
    seen_gate_rooms: set[tuple[str, tuple[int, int]]] = set()
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
        # -- a point anchor advertises exactly one eligible entry direction;
        #    the cell that direction leads to must be provider-valid. Other
        #    directions are ordinary terrain steps and follow the provider's
        #    own validity, so a coastal cave may be authored next to water.
        if entry.is_point_shape and entry.anchor_cell is not None:
            for gate in entry.gates:
                dx, dy = DIRECTION_DELTAS[gate.return_direction]
                neighbor = (entry.anchor_cell[0] + dx, entry.anchor_cell[1] + dy)
                if not provider_valid_outside_footprints(neighbor):
                    fail(
                        anchor_key,
                        f"point anchor {entry.anchor_cell} has provider-invalid neighbor {neighbor} in its entry direction",
                    )

    # -- one grid room hosts one gate: two gates sharing a destination room
    #    would collide on the room's single WildernessGateExit slot and leave
    #    one gate unprovisionable. Checked after the per-entry rules so every
    #    more precise collision rule keeps naming its own cause.
    for anchor_key, gate in gate_rooms:
        gate_room = (gate.z_map_key, settlement_position(index, gate.destination))
        if gate_room in seen_gate_rooms:
            fail(anchor_key, f"gate {gate.return_direction!r} shares destination room {gate_room} with another gate")
        seen_gate_rooms.add(gate_room)


WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint] = {
    "capital_altoria": WildernessEntryPoint(
        anchor_key="capital_altoria",
        # The city's rasterized physical envelope at the one-kilometre
        # wilderness scale (world-map-scale design §8/§10.3): an irregular
        # 40 km² built-up mask inside a seven-by-nine-kilometre box, replacing
        # the old 5x5 ten-kilometre block. The mask rows are contract: the
        # derived anchor cell is the plaza cell (860, 1080), and the south and
        # east gate rays leave the mask at (860, 1077) and (864, 1080).
        shape=(
            "#.....#",
            "##...##",
            ".#####.",
            "#######",
            "#######",
            "####..#",
            "#..#.##",
            "####...",
            "..##...",
        ),
        origin_xy=(857, 1076),
        gates=(
            # 南門: a traveler at (860, 1077) heading north enters the city.
            WildernessGate("n", settlement_node_ref("capital_altoria", "south_gate")),
            # 東門: a traveler at (864, 1080) heading west enters the city.
            WildernessGate("w", settlement_node_ref("capital_altoria", "east_gate")),
        ),
    ),
    "village_ciaran": WildernessEntryPoint(
        anchor_key="village_ciaran",
        # The hidden village is a point entrance, not a nine-square-kilometre
        # obstacle at the new scale (design §9/§10.3): the plaza cell itself,
        # entered only from its authored direction. The hidden path's physical
        # position (35, 270) transforms inside this same cell.
        shape=("#",),
        origin_xy=(1340, 1220),
        gates=(
            # 隱密小徑: a traveler at the anchor cell heading north follows the
            # concealed path into the village. No other direction is a
            # gateway.
            WildernessGate("n", settlement_node_ref("village_ciaran", "hidden_path")),
        ),
    ),
}
