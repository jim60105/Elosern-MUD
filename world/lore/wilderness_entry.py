"""Wilderness entry registry: which grid-placed anchor owns which wilderness
footprint, and which face-gates of that footprint lead back to its grid rooms
(wilderness-anchor-footprint Model A).

Each settlement document's ``wilderness_entry`` row is the authored source; this
module exposes the composed view of the published settlement world (the DB
mirror in ``world.lore.sync`` is a projection of it). All geometry helpers are
pure and derived from the authored mask — consumers never re-derive it.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import ReferenceError, settlement_node_ref, settlement_position

from world.maps.published import PublishedView

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

    def approach_cell(
        self,
        gate: WildernessGate,
        *,
        bounds: tuple[int, int] | None = None,
    ) -> tuple[int, int] | None:
        """The exterior cell a wilderness traveler stands on to take ``gate``.

        ``bounds`` defaults to the published provider frame; a candidate
        validator passes its own explicit ``(max_x, max_y)`` so it never has
        to publish a world to check one.

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
        while cell in footprint and _in_provider_rect(cell, bounds):
            crossed = True
            cell = (cell[0] + dx, cell[1] + dy)
        if not crossed or not _in_provider_rect(cell, bounds):
            return None
        return cell


def _in_provider_rect(
    cell: tuple[int, int], bounds: tuple[int, int] | None = None
) -> bool:
    max_x, max_y = _provider_bounds() if bounds is None else bounds
    x, y = cell
    return 0 <= x <= max_x and 0 <= y <= max_y
#: The composed wilderness gateways of the published settlements, keyed by the
#: anchor (``location_ref``) whose footprint and gates they declare. A
#: settlement with no ``wilderness_entry`` row has no wilderness gateway.
WILDERNESS_ENTRY_REGISTRY: Mapping[str, WildernessEntryPoint] = PublishedView(
    "wilderness_entries"
)
