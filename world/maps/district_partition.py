"""Frozen map-district partition: read-only runtime lookup (map-district-partition).

``world/maps/data/district_partition.json`` is generated offline by
``uv run --locked python -m tools.map_district_partition`` and committed. This
module is the game adapter: it binds the artifact's path and the published
mainland land rule to the pure codec in ``elosern_map_core.partition_codec``,
which decodes the document, reports its metadata and compares its source
dependency signature. It imports no generator, NumPy or SciPy, so a runtime
process decodes and freshness-checks the artifact with the generation extra
absent.

The document layout is owned by the codec; see its module docstring. A lookup
first checks the mainland polygon (sea has no owner), then the exception tile,
then the coarse run.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path

from elosern_map_core.partition_codec import (
    DistrictPartition,
    PartitionFreshness,
    PartitionMetadata,
    decode_partition as _decode_partition,
    partition_freshness,
    partition_source_signature,
    read_partition_metadata,
)
from elosern_map_core.sources import discover_source_documents
from world.lore.wilderness_regions import is_on_mainland

#: The repository root the authored sources are discovered from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = Path(__file__).resolve().parent / "data" / "district_partition.json"


def _mainland_cell(cell: tuple[int, int]) -> bool:
    """The shared land rule: the cell's centre lies inside the mainland."""
    return is_on_mainland(cell[0] + 0.5, cell[1] + 0.5)


def decode_partition(
    document: Mapping,
    is_land: Callable[[tuple[int, int]], bool] = _mainland_cell,
) -> DistrictPartition:
    """Decode and shape-check a partition document against the mainland rule."""
    return _decode_partition(document, is_land=is_land)


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


def artifact_metadata() -> PartitionMetadata:
    """The committed artifact's version and signatures, without expanding it."""
    return read_partition_metadata(DATA_PATH.read_text(encoding="utf-8"))


def current_source_signature(root: str | Path | None = None) -> str:
    """The conservative source dependency signature of the authored map sources."""
    base = Path(root) if root is not None else REPOSITORY_ROOT
    return partition_source_signature(discover_source_documents(base))


def freshness(root: str | Path | None = None) -> PartitionFreshness:
    """Whether the committed artifact describes the current sources.

    This is the only currency claim the runtime makes: the lookups above read
    the frozen ownership unconditionally, and a stale artifact reports
    ``current=False`` here rather than being presented as up to date.
    """
    return partition_freshness(artifact_metadata(), current_source_signature(root))
