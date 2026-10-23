"""Frozen map-district partition: read-only runtime lookup (map-district-partition).

``world/maps/data/district_partition.json`` is generated offline by
``uv run --locked python -m tools.map_district_partition`` and committed. This
module only decodes it: it never imports the generator or recomputes any
ownership, so a stale file is caught by the recomputation test instead of
being silently replaced at runtime.

Layout of the document (all integers):

* ``frame_cells`` (2700) one-kilometre cells per side, split into
  ``tile_cells`` (5) kilometre tiles, 540 per side.
* ``districts``: the district keys in sorted order; an owner code is the
  key's index plus one, and 0 means no owner (sea).
* ``coarse``: one row per tile row, south to north, as flat
  ``[code, count, ...]`` runs over tile columns. ``-1`` marks a tile whose
  land cells have several owners.
* ``exceptions``: ``[tx, ty, code, count, ...]`` runs of the 25 exact cell
  owners of each such tile, row-major from its south-west cell, sea as 0.
* ``outlines``: per district, rings of ``[x0, y0, x1, y1, ...]`` metres in
  the continental east/north frame; outer rings run counter-clockwise and
  holes clockwise.

A lookup first checks the mainland polygon (sea has no owner), then the
exception tile, then the coarse run.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType

from world.lore.wilderness_regions import is_on_mainland

DATA_PATH = Path(__file__).resolve().parent / "data" / "district_partition.json"

#: The document version this reader decodes.
FORMAT_VERSION = 1
#: Coarse tile value whose cells are listed in ``exceptions``.
MIXED = -1


class DistrictPartitionError(ValueError):
    """The frozen partition document is malformed."""


def _mainland_cell(cell: tuple[int, int]) -> bool:
    """The shared land rule: the cell's centre lies inside the mainland."""
    return is_on_mainland(cell[0] + 0.5, cell[1] + 0.5)


def _expand(runs, length: int, what: str) -> tuple[int, ...]:
    if len(runs) % 2:
        raise DistrictPartitionError(f"{what} runs are not value/count pairs")
    values: list[int] = []
    for value, count in zip(runs[::2], runs[1::2]):
        if not isinstance(value, int) or not isinstance(count, int) or count < 1:
            raise DistrictPartitionError(f"{what} holds a malformed run")
        values.extend([value] * count)
    if len(values) != length:
        raise DistrictPartitionError(f"{what} decodes to {len(values)} values, not {length}")
    return tuple(values)


@dataclass(frozen=True, eq=False)
class DistrictPartition:
    """The decoded partition; :meth:`district_at` is the runtime lookup."""

    fingerprint: str
    frame_cells: int
    tile_cells: int
    district_keys: tuple[str, ...]
    coarse: tuple[tuple[int, ...], ...]
    exceptions: Mapping[tuple[int, int], tuple[int, ...]]
    outlines: Mapping[str, tuple[tuple[int, ...], ...]]
    is_land: Callable[[tuple[int, int]], bool] = _mainland_cell

    def owner_code(self, cell: tuple[int, int]) -> int:
        """The stored owner code of an in-frame cell, ignoring the land rule."""
        x, y = cell
        tile = self.tile_cells
        tx, ty = x // tile, y // tile
        exact = self.exceptions.get((tx, ty))
        if exact is not None:
            return exact[(y % tile) * tile + x % tile]
        return self.coarse[ty][tx]

    def district_at(self, cell: tuple[int, int]) -> str | None:
        """The district key owning a one-kilometre cell; ``None`` for sea."""
        x, y = cell
        if not (0 <= x < self.frame_cells and 0 <= y < self.frame_cells):
            return None
        if not self.is_land((x, y)):
            return None
        code = self.owner_code((x, y))
        return self.district_keys[code - 1] if code > 0 else None


def decode_partition(
    document: Mapping,
    is_land: Callable[[tuple[int, int]], bool] = _mainland_cell,
) -> DistrictPartition:
    """Decode and shape-check a partition document."""
    if document.get("version") != FORMAT_VERSION:
        raise DistrictPartitionError(f"unsupported partition version {document.get('version')!r}")
    frame, tile = document["frame_cells"], document["tile_cells"]
    if not isinstance(frame, int) or not isinstance(tile, int) or tile < 1 or frame % tile:
        raise DistrictPartitionError("frame_cells is not a multiple of tile_cells")
    count = frame // tile
    keys = tuple(document["districts"])
    if list(keys) != sorted(set(keys)):
        raise DistrictPartitionError("district keys are not unique and sorted")
    rows = document["coarse"]
    if len(rows) != count:
        raise DistrictPartitionError(f"coarse has {len(rows)} rows, not {count}")
    coarse = tuple(_expand(row, count, f"coarse row {ty}") for ty, row in enumerate(rows))
    exceptions: dict[tuple[int, int], tuple[int, ...]] = {}
    for entry in document["exceptions"]:
        if len(entry) < 2 or not all(isinstance(value, int) for value in entry[:2]):
            raise DistrictPartitionError("an exception entry has no integer tile position")
        tx, ty = entry[0], entry[1]
        if not (0 <= tx < count and 0 <= ty < count) or coarse[ty][tx] != MIXED:
            raise DistrictPartitionError(f"exception tile {(tx, ty)} is not a mixed tile")
        if (tx, ty) in exceptions:
            raise DistrictPartitionError(f"exception tile {(tx, ty)} is listed twice")
        cells = _expand(entry[2:], tile * tile, f"exception tile {(tx, ty)}")
        if any(code < 0 for code in cells):
            raise DistrictPartitionError(f"exception tile {(tx, ty)} holds a mixed marker")
        exceptions[(tx, ty)] = cells
    mixed = sum(row.count(MIXED) for row in coarse)
    if mixed != len(exceptions):
        raise DistrictPartitionError("a mixed coarse tile has no exception entry")
    codes = {value for row in coarse for value in row} | {
        value for values in exceptions.values() for value in values
    }
    if any(not MIXED <= code <= len(keys) for code in codes):
        raise DistrictPartitionError("an owner code names no district")
    outlines = document["outlines"]
    if set(outlines) != set(keys):
        raise DistrictPartitionError("outlines do not cover exactly the districts")
    for key, rings in outlines.items():
        for ring in rings:
            if len(ring) % 2 or not all(isinstance(value, int) for value in ring):
                raise DistrictPartitionError(f"outline of {key!r} holds a malformed ring")
    return DistrictPartition(
        fingerprint=document["fingerprint"],
        frame_cells=frame,
        tile_cells=tile,
        district_keys=keys,
        coarse=coarse,
        exceptions=MappingProxyType(exceptions),
        outlines=MappingProxyType(
            {key: tuple(tuple(ring) for ring in outlines[key]) for key in keys}
        ),
        is_land=is_land,
    )


@cache
def frozen_partition() -> DistrictPartition:
    """The committed partition, decoded once per process."""
    return decode_partition(json.loads(DATA_PATH.read_text(encoding="utf-8")))


def district_at(cell: tuple[int, int]) -> str | None:
    """The map district owning wilderness cell ``(x, y)``; ``None`` for sea."""
    return frozen_partition().district_at(tuple(cell))


def district_outlines() -> Mapping[str, tuple[tuple[int, ...], ...]]:
    """Smoothed outline rings per district key (flat metre coordinates)."""
    return frozen_partition().outlines
