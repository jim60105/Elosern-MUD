"""Runtime adapter and bounded LRU cache for wilderness elevation lookups.

This module is part of the deterministic game runtime. It imports no NumPy or
SciPy and never runs implicit import-time loaders or zero-elevation fallbacks.
Elevation data is admitted and published through the single-writer runtime bundle
in :mod:`world.maps.runtime`.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from elosern_map_core.elevation_codec import (
    DEFAULT_CONFIG_DIGEST,
    ELEVATION_ALGORITHM_VERSION,
    ELEVATION_TILE_CELLS,
    MAX_ELEVATION_BYTES,
    ElevationBoundsError,
    ElevationBudgetExceededError,
    ElevationCorruptionError,
    ElevationDocumentError,
    ElevationFreshness,
    ElevationMetadata,
    ElevationTileCorruptionError,
    decode_tile,
    elevation_freshness as _elevation_freshness,
    elevation_source_signature,
    read_elevation_metadata as _read_elevation_metadata,
    verify_elevation_data_integrity,
)

#: Repository root the authored sources are discovered from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

#: Standard on-disk location of the generated elevation artifact.
DATA_PATH = REPOSITORY_ROOT / "content" / "maps" / "wilderness_elevation.json"


class ElevationNotLoadedError(RuntimeError):
    """An elevation lookup was attempted before an accepted bundle was published."""


class ElevationTileCache:
    """Bounded LRU cache for decoded 4096-byte elevation tiles."""

    def __init__(self, maxsize: int = 128) -> None:
        self._maxsize = maxsize
        self._cache: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()

    def get(self, key: tuple[str, int, int]) -> bytes | None:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: tuple[str, int, int], value: bytes) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return
        if len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: tuple[str, int, int]) -> bool:
        return key in self._cache


class ElevationRuntime:
    """An admitted elevation artifact and its tile lookup surface."""

    def __init__(
        self,
        metadata: ElevationMetadata,
        tiles: Mapping[tuple[int, int], str],
        cache: ElevationTileCache | None = None,
    ) -> None:
        self.metadata = metadata
        self._tiles = dict(tiles)
        self._cache = cache if cache is not None else ElevationTileCache(128)
        self.frame_cells = metadata.frame_cells
        self.tile_cells = metadata.tile_cells

    @property
    def fingerprint(self) -> str:
        return self.metadata.fingerprint

    def get_tile(self, tx: int, ty: int) -> bytes:
        """Decode or retrieve one tile from the bounded cache."""
        key = (self.fingerprint, tx, ty)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        raw_b64 = self._tiles.get((tx, ty))
        if raw_b64 is None:
            raise ElevationBoundsError(f"tile coordinate ({tx}, {ty}) not found in artifact")

        decoded = decode_tile(
            raw_b64,
            tx=tx,
            ty=ty,
            frame_cells=self.frame_cells,
            tile_cells=self.tile_cells,
        )
        self._cache.put(key, decoded)
        return decoded

    def cell_elevation(self, x: int, y: int) -> tuple[int, int]:
        """The (band, prominence_tier) of one in-frame cell."""
        if isinstance(x, bool) or not isinstance(x, int) or isinstance(y, bool) or not isinstance(y, int):
            raise ElevationBoundsError(f"cell coordinates must be integers, got ({x!r}, {y!r})")
        if not (0 <= x < self.frame_cells and 0 <= y < self.frame_cells):
            raise ElevationBoundsError(
                f"cell ({x}, {y}) outside legal frame 0..{self.frame_cells - 1}"
            )

        tx = x // self.tile_cells
        ty = y // self.tile_cells
        lx = x % self.tile_cells
        ly = y % self.tile_cells

        tile_bytes = self.get_tile(tx, ty)
        byte_val = tile_bytes[ly * self.tile_cells + lx]
        band = byte_val >> 4
        tier = byte_val & 0x03
        return band, tier

    def band(self, x: int, y: int) -> int:
        """The elevation band (0..15) of wilderness cell (x, y)."""
        return self.cell_elevation(x, y)[0]

    def prominence_tier(self, x: int, y: int) -> int:
        """The prominence tier (0..3) of wilderness cell (x, y)."""
        return self.cell_elevation(x, y)[1]


_CURRENT_ELEVATION: ElevationRuntime | None = None


def _install(runtime: ElevationRuntime | None) -> None:
    """Point the global elevation lookup at one admitted runtime."""
    global _CURRENT_ELEVATION
    _CURRENT_ELEVATION = runtime


def current() -> ElevationRuntime:
    """The currently published ElevationRuntime, or raise if none loaded."""
    if _CURRENT_ELEVATION is None:
        raise ElevationNotLoadedError(
            "no elevation artifact is currently published; adopt an accepted world first"
        )
    return _CURRENT_ELEVATION


def is_loaded() -> bool:
    """Whether an admitted elevation runtime is currently published."""
    return _CURRENT_ELEVATION is not None


def cell_elevation(x: int, y: int) -> tuple[int, int]:
    """The (band, prominence_tier) of cell (x, y) through the published bundle."""
    return current().cell_elevation(x, y)


def band(x: int, y: int) -> int:
    """The elevation band of cell (x, y) through the published bundle."""
    return current().band(x, y)


def prominence_tier(x: int, y: int) -> int:
    """The prominence tier of cell (x, y) through the published bundle."""
    return current().prominence_tier(x, y)


def load_elevation(
    root: str | Path | None = None,
    expected_frame_cells: int | None = None,
) -> ElevationRuntime:
    """Load, verify and index one elevation artifact without expanding rasters."""
    path = Path(root) / "content" / "maps" / "wilderness_elevation.json" if root is not None else DATA_PATH
    if not path.is_file():
        raise ElevationDocumentError(f"elevation artifact {path} does not exist")

    size = path.stat().st_size
    if size > MAX_ELEVATION_BYTES:
        raise ElevationBudgetExceededError(
            f"elevation artifact {path} is {size} bytes, exceeds {MAX_ELEVATION_BYTES} (4 MiB)"
        )

    text = path.read_text(encoding="utf-8")
    try:
        doc = json.loads(text)
        metadata = verify_elevation_data_integrity(doc, expected_frame_cells=expected_frame_cells)
        tiles_map: dict[tuple[int, int], str] = {}
        for tile in doc.get("tiles", ()):
            tiles_map[(tile["x"], tile["y"])] = tile["data"]
    except (json.JSONDecodeError, TypeError, AttributeError, KeyError) as error:
        raise ElevationCorruptionError(f"malformed elevation artifact structure: {error}") from error

    return ElevationRuntime(
        metadata=metadata,
        tiles=tiles_map,
        cache=ElevationTileCache(128),
    )


def artifact_metadata(root: str | Path | None = None) -> ElevationMetadata:
    """Read the artifact's metadata and signatures without expanding it."""
    path = Path(root) / "content" / "maps" / "wilderness_elevation.json" if root is not None else DATA_PATH
    if not path.is_file():
        raise ElevationDocumentError(f"elevation artifact {path} does not exist")
    return _read_elevation_metadata(path.read_text(encoding="utf-8"))


def current_source_signature(
    continent_fingerprint: str,
    config_digest: str = DEFAULT_CONFIG_DIGEST,
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
) -> list[dict[str, str]]:
    """The conservative source dependency signature of the elevation inputs."""
    return elevation_source_signature(
        continent_fingerprint=continent_fingerprint,
        config_digest=config_digest,
        algorithm_version=algorithm_version,
    )


def freshness(
    metadata: ElevationMetadata,
    continent_fingerprint: str,
    config_digest: str = DEFAULT_CONFIG_DIGEST,
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
) -> ElevationFreshness:
    """Whether the committed elevation artifact describes the current sources."""
    expected = current_source_signature(
        continent_fingerprint=continent_fingerprint,
        config_digest=config_digest,
        algorithm_version=algorithm_version,
    )
    return _elevation_freshness(metadata, expected, algorithm_version=algorithm_version)
