"""Frozen wilderness road artifact: lightweight decoding, metadata and freshness.

This module is the runtime-neutral half of the road network. It reads the
committed artifact's version, algorithm version, source dependency signature
and the road routes with the standard library only: it imports no NumPy, no
SciPy, no game module and no generator, so a game or editor process can decode
the network and answer "is this artifact current?" without the generation extra
installed.

The offline generator is a separate unit and is the only producer of the text
this reader accepts.

Artifact layout, one road per line::

    {
      "algorithm_version": 1,
      "fingerprint": "<road_fingerprint>",
      "frame_cells": 2700,
      "nodes": ["<key>"],
      "roads": [
        {"cells": [0, 0, 1, 1], "first": "<key>", "second": "<key>"}
      ],
      "source_signature": "<sha256>",
      "version": 1
    }

* ``version`` -- the document format this reader supports (:data:`FORMAT_VERSION`).
* ``algorithm_version`` -- :data:`ROAD_ALGORITHM_VERSION` of the generator.
* ``source_signature`` -- :func:`road_source_signature` over every authored road
  input, the elevation fingerprint and the authored region speeds.
* ``fingerprint`` -- :func:`road_fingerprint` over the network itself.
* ``nodes`` -- the settlement keys the network joins, sorted.
* ``roads`` -- ``first`` and ``second`` settlement keys with ``first < second``,
  sorted by that pair, and ``cells`` a flat ``[x0, y0, x1, y1, ...]`` route.

``encode_road_document`` sorts and canonicalises, so identical networks encode to
identical bytes; ``decode_road_network`` rejects anything a producer could not
have written.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .sources import expected_document

#: The document format this reader decodes. A format bump accompanies any
#: change to the artifact's fields or their meaning.
FORMAT_VERSION = 1
#: Bump when the road algorithm or its encoding changes; the artifact and every
#: freshness check carry it.
ROAD_ALGORITHM_VERSION = 1
#: The authored document kinds the network input depends on. Interiors and
#: districts cannot move a road, so they never invalidate freshness.
ROAD_SOURCE_KINDS = frozenset({"continent", "locations", "settlement", "road_network"})


class RoadDocumentError(ValueError):
    """The frozen road document is malformed."""


@dataclass(frozen=True, slots=True)
class RoadFreshness:
    """One road artifact's freshness against the current map inputs."""

    algorithm_version: int
    input_signature: str
    current: bool


@dataclass(frozen=True, slots=True)
class RoadMetadata:
    """The artifact's cheap identity: no road route is expanded."""

    format_version: int
    algorithm_version: int
    source_signature: str
    fingerprint: str


@dataclass(frozen=True, eq=False)
class RoadNetwork:
    """A decoded network; ``roads`` is sorted by its settlement pair."""

    fingerprint: str
    nodes: tuple[str, ...]
    roads: tuple[tuple[str, str, tuple[tuple[int, int], ...]], ...]
    cells: frozenset[tuple[int, int]]


def _document(source: Mapping | str) -> Mapping:
    if isinstance(source, str):
        try:
            loaded = json.loads(source)
        except json.JSONDecodeError as error:
            raise RoadDocumentError("road document is not valid JSON") from error
    else:
        loaded = source
    if not isinstance(loaded, Mapping):
        raise RoadDocumentError("road document root is not a mapping")
    return loaded


def _require_version(document: Mapping) -> None:
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != FORMAT_VERSION:
        raise RoadDocumentError(f"unsupported road version {version!r}")


def _require_text(document: Mapping, field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise RoadDocumentError(f"road {field} is missing")
    return value


def _feed(digest: "hashlib._Hash", value: str) -> None:
    digest.update(value.encode("utf-8"))
    digest.update(b"\0")


def read_road_metadata(source: Mapping | str) -> RoadMetadata:
    """Read the artifact's version and signatures without expanding any route."""
    document = _document(source)
    _require_version(document)
    algorithm = document.get("algorithm_version")
    if isinstance(algorithm, bool) or not isinstance(algorithm, int) or algorithm < 1:
        raise RoadDocumentError("road algorithm_version is missing")
    return RoadMetadata(
        format_version=FORMAT_VERSION,
        algorithm_version=algorithm,
        source_signature=_require_text(document, "source_signature"),
        fingerprint=_require_text(document, "fingerprint"),
    )


def road_freshness(
    metadata: RoadMetadata,
    source_signature: str | None,
    algorithm_version: int = ROAD_ALGORITHM_VERSION,
) -> RoadFreshness:
    """Whether ``metadata`` describes the current inputs and algorithm.

    A missing current signature is never current: an unreadable or absent
    source set cannot certify a stale network as fresh.
    """
    current = (
        metadata.format_version == FORMAT_VERSION
        and metadata.algorithm_version == algorithm_version
        and bool(source_signature)
        and metadata.source_signature == source_signature
    )
    return RoadFreshness(
        algorithm_version=metadata.algorithm_version,
        input_signature=metadata.source_signature,
        current=current,
    )


def road_source_signature(
    fingerprints: Mapping[str, str],
    *,
    elevation_fingerprint: str,
    region_speeds: Mapping[str, int],
) -> str:
    """The signature of every input the road network depends on.

    ``fingerprints`` is a ``{relative_path: fingerprint}`` source set; only the
    road source kinds count, so an interior or district edit leaves the network
    current. The elevation fingerprint and the authored region speeds join the
    digest because terrain and terrain price both shape the routed roads.
    A published world retains the fingerprints it was built from, so signing
    those binds an artifact to the exact sources behind its roads.
    """
    digest = hashlib.sha256()
    rows: list[tuple[str, str]] = []
    for relative_path, fingerprint in fingerprints.items():
        expected = expected_document(relative_path)
        if expected is None or expected[0] not in ROAD_SOURCE_KINDS:
            continue
        rows.append((relative_path.replace("\\", "/"), fingerprint))
    for relative_path, fingerprint in sorted(rows):
        _feed(digest, relative_path)
        _feed(digest, fingerprint)
    _feed(digest, elevation_fingerprint)
    for region, speed in sorted(region_speeds.items()):
        _feed(digest, region)
        _feed(digest, str(int(speed)))
    return digest.hexdigest()


def _flat(cells: Sequence[tuple[int, int]]) -> list[int]:
    return [value for cell in cells for value in (int(cell[0]), int(cell[1]))]


def road_fingerprint(
    nodes: Sequence[str],
    roads: Sequence[tuple[str, str, Sequence[tuple[int, int]]]],
) -> str:
    """The canonical digest of a network in the order the caller supplies.

    Encoding and decoding both call it over their own canonical order, so the
    two can never drift.
    """
    document = {
        "nodes": [str(node) for node in nodes],
        "roads": [
            [str(first), str(second), _flat(cells)] for first, second, cells in roads
        ],
    }
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode_road_document(
    *,
    frame_cells: int,
    source_signature: str,
    nodes: Sequence[str],
    roads: Sequence[tuple[str, str, Sequence[tuple[int, int]]]],
) -> str:
    """Encode one network as the canonical artifact text."""
    ordered_nodes = sorted(str(node) for node in nodes)
    ordered_roads: list[tuple[str, str, Sequence[tuple[int, int]]]] = []
    for first, second, cells in roads:
        if not isinstance(first, str) or not isinstance(second, str) or first >= second:
            raise RoadDocumentError(
                f"road endpoints {first!r} and {second!r} are not in canonical order"
            )
        if not cells:
            raise RoadDocumentError("a road has no cells")
        ordered_roads.append((first, second, cells))
    ordered_roads.sort(key=lambda row: (row[0], row[1]))
    fingerprint = road_fingerprint(ordered_nodes, ordered_roads)
    rows = [
        {"cells": _flat(cells), "first": str(first), "second": str(second)}
        for first, second, cells in ordered_roads
    ]
    lines = [
        "{",
        f'  "algorithm_version": {ROAD_ALGORITHM_VERSION},',
        f'  "fingerprint": {json.dumps(fingerprint, ensure_ascii=False)},',
        f'  "frame_cells": {int(frame_cells)},',
        f'  "nodes": {json.dumps(ordered_nodes, ensure_ascii=False)},',
    ]
    if rows:
        lines.append('  "roads": [')
        lines.append(
            ",\n".join(
                "    "
                + json.dumps(
                    row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                for row in rows
            )
        )
        lines.append("  ],")
    else:
        lines.append('  "roads": [],')
    lines.extend(
        [
            f'  "source_signature": {json.dumps(source_signature, ensure_ascii=False)},',
            f'  "version": {FORMAT_VERSION}',
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def _require_frame(document: Mapping) -> int:
    frame = document.get("frame_cells")
    if isinstance(frame, bool) or not isinstance(frame, int) or frame < 1:
        raise RoadDocumentError("road frame_cells is missing")
    return frame


def _require_nodes(document: Mapping) -> tuple[str, ...]:
    nodes = document.get("nodes")
    if not isinstance(nodes, list) or any(not isinstance(node, str) for node in nodes):
        raise RoadDocumentError("road nodes is not a list of settlement keys")
    return tuple(nodes)


def _require_cells(row: Mapping, frame: int) -> tuple[tuple[int, int], ...]:
    raw = row.get("cells")
    if not isinstance(raw, list) or not raw or len(raw) % 2:
        raise RoadDocumentError("a road's cells is not a non-empty cell list")
    cells: list[tuple[int, int]] = []
    for index in range(0, len(raw), 2):
        x, y = raw[index], raw[index + 1]
        for value in (x, y):
            if isinstance(value, bool) or not isinstance(value, int):
                raise RoadDocumentError("a road cell coordinate is not an integer")
            if not 0 <= value < frame:
                raise RoadDocumentError(
                    f"road cell ({x}, {y}) outside the legal frame 0..{frame - 1}"
                )
        cells.append((x, y))
    return tuple(cells)


def decode_road_network(source: Mapping | str) -> RoadNetwork:
    """Decode and shape-check a road document."""
    document = _document(source)
    metadata = read_road_metadata(document)
    frame = _require_frame(document)
    nodes = _require_nodes(document)
    entries = document.get("roads")
    if not isinstance(entries, list):
        raise RoadDocumentError("roads is not a list")
    decoded: list[tuple[str, str, tuple[tuple[int, int], ...]]] = []
    for row in entries:
        if not isinstance(row, Mapping):
            raise RoadDocumentError("a road entry is not a mapping")
        first, second = row.get("first"), row.get("second")
        if not isinstance(first, str) or not isinstance(second, str):
            raise RoadDocumentError("a road endpoint is not a settlement key")
        if first >= second:
            raise RoadDocumentError(
                f"road endpoints {first!r} and {second!r} are not in canonical order"
            )
        decoded.append((first, second, _require_cells(row, frame)))
    if metadata.fingerprint != road_fingerprint(nodes, decoded):
        raise RoadDocumentError("road fingerprint does not match its roads")
    return RoadNetwork(
        fingerprint=metadata.fingerprint,
        nodes=tuple(sorted(nodes)),
        roads=tuple(sorted(decoded, key=lambda row: (row[0], row[1]))),
        cells=frozenset(cell for _, _, cells in decoded for cell in cells),
    )


__all__ = [
    "FORMAT_VERSION",
    "ROAD_ALGORITHM_VERSION",
    "ROAD_SOURCE_KINDS",
    "RoadDocumentError",
    "RoadFreshness",
    "RoadMetadata",
    "RoadNetwork",
    "decode_road_network",
    "encode_road_document",
    "read_road_metadata",
    "road_fingerprint",
    "road_freshness",
    "road_source_signature",
]
