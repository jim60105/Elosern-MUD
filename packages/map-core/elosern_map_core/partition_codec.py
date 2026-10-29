"""Frozen district-partition artifact: lightweight decoding, metadata and freshness.

This module is the runtime half of the district partition. It reads the
committed artifact's version, algorithm version, source dependency signature
and ownership/outline payload with the standard library only: it imports no
NumPy, SciPy, game module or generator, so a game or editor process can decode
the partition and answer "is this artifact current?" without the generation
extra installed.

The generation half lives in :mod:`elosern_map_core.partition`, which is only
imported by the offline generator.

Artifact layout (all integers unless stated):

* ``version`` -- the document format this reader supports (:data:`FORMAT_VERSION`).
* ``algorithm_version`` -- :data:`PARTITION_ALGORITHM_VERSION` of the generator
  that produced the ownership and outlines.
* ``source_signature`` -- :func:`partition_source_signature` over the authored
  map sources the partition depends on (a conservative superset: any edit to a
  partition source changes it).
* ``fingerprint`` -- the generator's exact raster input fingerprint.
* ``frame_cells`` / ``tile_cells`` -- 2,700 cells, split into 5 km tiles.
* ``districts`` -- district keys in sorted order; an owner code is the key's
  index plus one and 0 means sea.
* ``coarse`` -- one row per tile row, south to north, as flat
  ``[code, count, ...]`` runs; ``-1`` marks a tile whose land has several owners.
* ``exceptions`` -- ``[tx, ty, code, count, ...]`` runs of the 25 exact cell
  owners of each mixed tile, row-major from its south-west cell.
* ``outlines`` -- per district, rings of ``[x0, y0, x1, y1, ...]`` metres in the
  continental east/north frame.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .sources import expected_document

#: The document format this reader decodes. A format bump accompanies any
#: change to the artifact's fields or their meaning.
FORMAT_VERSION = 2
#: Bump when the partition algorithm or its encoding changes; the artifact and
#: every runtime freshness check carry it.
PARTITION_ALGORITHM_VERSION = 1
#: The authored document kinds the partition input depends on. Interiors and
#: editor layouts cannot change ownership, so they never invalidate freshness.
PARTITION_SOURCE_KINDS = frozenset({"continent", "locations", "districts", "settlement"})
#: Coarse tile value whose cells are listed in ``exceptions``.
MIXED = -1


class PartitionDocumentError(ValueError):
    """The frozen partition document is malformed."""


@dataclass(frozen=True, slots=True)
class PartitionFreshness:
    """One partition artifact's freshness against the current map inputs."""

    algorithm_version: int
    input_signature: str
    current: bool


@dataclass(frozen=True, slots=True)
class PartitionMetadata:
    """The artifact's cheap identity: no ownership raster is expanded."""

    format_version: int
    algorithm_version: int
    source_signature: str
    fingerprint: str


@dataclass(frozen=True, eq=False)
class DistrictPartition:
    """A decoded partition; :meth:`district_at` is the runtime lookup."""

    fingerprint: str
    frame_cells: int
    tile_cells: int
    district_keys: tuple[str, ...]
    coarse: tuple[tuple[int, ...], ...]
    exceptions: Mapping[tuple[int, int], tuple[int, ...]]
    outlines: Mapping[str, tuple[tuple[int, ...], ...]]
    is_land: Callable[[tuple[int, int]], bool]

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


def _document(source: Mapping | str) -> Mapping:
    if isinstance(source, str):
        return json.loads(source)
    return source


def _require_version(document: Mapping) -> None:
    if document.get("version") != FORMAT_VERSION:
        raise PartitionDocumentError(
            f"unsupported partition version {document.get('version')!r}"
        )


def _require_text(document: Mapping, field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise PartitionDocumentError(f"partition {field} is missing")
    return value


def read_partition_metadata(source: Mapping | str) -> PartitionMetadata:
    """Read the artifact's version and signatures without expanding any raster."""
    document = _document(source)
    _require_version(document)
    algorithm = document.get("algorithm_version")
    if isinstance(algorithm, bool) or not isinstance(algorithm, int) or algorithm < 1:
        raise PartitionDocumentError("partition algorithm_version is missing")
    return PartitionMetadata(
        format_version=FORMAT_VERSION,
        algorithm_version=algorithm,
        source_signature=_require_text(document, "source_signature"),
        fingerprint=_require_text(document, "fingerprint"),
    )


def partition_freshness(
    metadata: PartitionMetadata,
    source_signature: str | None,
    algorithm_version: int = PARTITION_ALGORITHM_VERSION,
) -> PartitionFreshness:
    """Whether ``metadata`` describes the current inputs and algorithm.

    A missing current signature is never current: an unreadable or absent
    source set cannot certify stale ownership as fresh.
    """
    current = (
        metadata.format_version == FORMAT_VERSION
        and metadata.algorithm_version == algorithm_version
        and bool(source_signature)
        and metadata.source_signature == source_signature
    )
    return PartitionFreshness(
        algorithm_version=metadata.algorithm_version,
        input_signature=metadata.source_signature,
        current=current,
    )


def partition_source_signature(
    documents: Iterable[Any],
) -> str:
    """The conservative signature of the map sources the partition depends on.

    ``documents`` are authored or source documents with ``relative_path`` and
    ``fingerprint``. Membership and content both count: adding, removing or
    editing a partition source changes the signature. The kind rule is
    :func:`elosern_map_core.sources.expected_document`, so the generator and
    every runtime caller classify a path identically.
    """
    return partition_source_signature_from_fingerprints(
        {document.relative_path: document.fingerprint for document in documents}
    )


def partition_source_signature_from_fingerprints(
    fingerprints: Mapping[str, str],
) -> str:
    """The same signature over a ``{relative_path: fingerprint}`` source set.

    A published world retains the fingerprints of the documents it was built
    from; signing those binds a generated artifact to the exact sources behind
    its ownership instead of a later, possibly changed, read of the files.
    """
    digest = hashlib.sha256()
    rows: list[tuple[str, str]] = []
    for relative_path, fingerprint in fingerprints.items():
        expected = expected_document(relative_path)
        if expected is None or expected[0] not in PARTITION_SOURCE_KINDS:
            continue
        rows.append((relative_path.replace("\\", "/"), fingerprint))
    for relative_path, fingerprint in sorted(rows):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(fingerprint.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _expand(runs, length: int, what: str) -> tuple[int, ...]:
    if len(runs) % 2:
        raise PartitionDocumentError(f"{what} runs are not value/count pairs")
    values: list[int] = []
    for value, count in zip(runs[::2], runs[1::2]):
        if isinstance(value, bool) or isinstance(count, bool):
            raise PartitionDocumentError(f"{what} holds a malformed run")
        if not isinstance(value, int) or not isinstance(count, int) or count < 1:
            raise PartitionDocumentError(f"{what} holds a malformed run")
        # Bound the allocation by the expected decoded length: a corrupt count
        # must be refused, not materialized first.
        if count > length - len(values):
            raise PartitionDocumentError(
                f"{what} runs decode to more than {length} values"
            )
        values.extend([value] * count)
    if len(values) != length:
        raise PartitionDocumentError(
            f"{what} decodes to {len(values)} values, not {length}"
        )
    return tuple(values)


def decode_partition(
    source: Mapping | str,
    is_land: Callable[[tuple[int, int]], bool],
) -> DistrictPartition:
    """Decode and shape-check a partition document.

    ``is_land`` is required: a coarse tile stores one code for its land, and
    only the caller's mainland rule can tell a sea cell of such a tile apart
    from land. The game adapter binds the published mainland polygon and
    therefore offers ``decode_partition(document)``; the core seam here is
    ``decode_partition(document, is_land)``.
    """
    document = _document(source)
    metadata = read_partition_metadata(document)
    frame, tile = document.get("frame_cells"), document.get("tile_cells")
    if (
        isinstance(frame, bool)
        or isinstance(tile, bool)
        or not isinstance(frame, int)
        or not isinstance(tile, int)
        or frame < 1
        or tile < 1
        or frame % tile
    ):
        raise PartitionDocumentError("frame_cells is not a multiple of tile_cells")
    count = frame // tile
    districts = document.get("districts")
    if not isinstance(districts, list) or any(not isinstance(key, str) for key in districts):
        raise PartitionDocumentError("districts is not a list of keys")
    keys = tuple(districts)
    if list(keys) != sorted(set(keys)):
        raise PartitionDocumentError("district keys are not unique and sorted")
    rows = document.get("coarse")
    if not isinstance(rows, list) or len(rows) != count:
        raise PartitionDocumentError(
            f"coarse has {len(rows) if isinstance(rows, list) else 0} rows, not {count}"
        )
    coarse = tuple(_expand(row, count, f"coarse row {ty}") for ty, row in enumerate(rows))
    exceptions: dict[tuple[int, int], tuple[int, ...]] = {}
    entries = document.get("exceptions")
    if not isinstance(entries, list):
        raise PartitionDocumentError("exceptions is not a list")
    for entry in entries:
        if not isinstance(entry, list) or len(entry) < 2:
            raise PartitionDocumentError("an exception entry has no integer tile position")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in entry[:2]):
            raise PartitionDocumentError("an exception entry has no integer tile position")
        tx, ty = entry[0], entry[1]
        if not (0 <= tx < count and 0 <= ty < count) or coarse[ty][tx] != MIXED:
            raise PartitionDocumentError(f"exception tile {(tx, ty)} is not a mixed tile")
        if (tx, ty) in exceptions:
            raise PartitionDocumentError(f"exception tile {(tx, ty)} is listed twice")
        cells = _expand(entry[2:], tile * tile, f"exception tile {(tx, ty)}")
        if any(code < 0 for code in cells):
            raise PartitionDocumentError(f"exception tile {(tx, ty)} holds a mixed marker")
        exceptions[(tx, ty)] = cells
    mixed = sum(row.count(MIXED) for row in coarse)
    if mixed != len(exceptions):
        raise PartitionDocumentError("a mixed coarse tile has no exception entry")
    codes = {value for row in coarse for value in row} | {
        value for values in exceptions.values() for value in values
    }
    if any(not MIXED <= code <= len(keys) for code in codes):
        raise PartitionDocumentError("an owner code names no district")
    outlines = document.get("outlines")
    if not isinstance(outlines, Mapping) or set(outlines) != set(keys):
        raise PartitionDocumentError("outlines do not cover exactly the districts")
    for key, rings in outlines.items():
        if not isinstance(rings, list):
            raise PartitionDocumentError(f"outline of {key!r} is not a list of rings")
        for ring in rings:
            if not isinstance(ring, list):
                raise PartitionDocumentError(f"outline of {key!r} holds a malformed ring")
            if len(ring) % 2 or not all(
                isinstance(value, int) and not isinstance(value, bool) for value in ring
            ):
                raise PartitionDocumentError(f"outline of {key!r} holds a malformed ring")
    return DistrictPartition(
        fingerprint=metadata.fingerprint,
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


__all__ = [
    "FORMAT_VERSION",
    "MIXED",
    "PARTITION_ALGORITHM_VERSION",
    "PARTITION_SOURCE_KINDS",
    "DistrictPartition",
    "PartitionDocumentError",
    "PartitionFreshness",
    "PartitionMetadata",
    "decode_partition",
    "partition_freshness",
    "partition_source_signature",
    "partition_source_signature_from_fingerprints",
    "read_partition_metadata",
]
