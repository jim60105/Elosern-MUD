"""Bounded pure-Python codec and integrity checks for wilderness elevation tiles.

This module belongs to the runtime half of the map system: it uses the standard
library only (no NumPy, SciPy, Evennia or Django) so it can be safely imported
and executed in any environment without offline generation dependencies.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import zlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

#: Version of the stored elevation artifact.
ELEVATION_FORMAT_VERSION = 1

#: Version of the deterministic generation algorithm.
ELEVATION_ALGORITHM_VERSION = 1

#: Cell dimension of each square tile.
ELEVATION_TILE_CELLS = 64

#: Maximum byte size of the serialized artifact (4 MiB).
MAX_ELEVATION_BYTES = 4 * 1024 * 1024

#: Canonical default configuration values mirroring DEFAULT_ELEVATION_CONFIG.
DEFAULT_CONFIG_VALUES: dict[str, Any] = {
    "amplitude_coast": 0.08,
    "amplitude_forest": 0.2,
    "amplitude_hills": 0.35,
    "amplitude_mountains": 0.4,
    "amplitude_open": 0.18,
    "base_wavelength": 16.0,
    "coast_max_rise": 6.0,
    "coast_rise_rate": 0.05,
    "lacunarity": 2.0,
    "min_cluster_area": 4,
    "noise_seed": 1337,
    "octaves": 4,
    "persistence": 0.5,
    "prominence_thresholds": [1.0, 2.0, 3.0],
    "quantization_scale": 1.0,
    "ridge_mountain_rise": 8.0,
    "ring_inner_radius": 3,
    "ring_outer_radius": 8,
    "river_carve_depth": 2.0,
    "seed": 42,
    "version": 1,
    "warp_strength": 6.0,
    "warp_wavelength": 32.0,
}


def _compute_config_digest(config_dict: Mapping[str, Any]) -> str:
    canonical = json.dumps(config_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


#: SHA-256 digest of the canonical default configuration.
DEFAULT_CONFIG_DIGEST = _compute_config_digest(DEFAULT_CONFIG_VALUES)


class ElevationDocumentError(ValueError):
    """The elevation artifact document is malformed or invalid."""


class ElevationCorruptionError(ElevationDocumentError):
    """The elevation artifact data fails integrity or format validation."""


class ElevationTileCorruptionError(ElevationCorruptionError):
    """A single elevation tile cannot be decoded or carries corrupt data."""


class ElevationBoundsError(IndexError, ValueError):
    """A cell lookup falls outside the legal frame cells."""


class ElevationBudgetExceededError(ElevationDocumentError):
    """The serialized elevation artifact exceeds the allowed byte budget."""


@dataclass(frozen=True, slots=True)
class ElevationMetadata:
    """The version, geometry and checksums of one elevation artifact."""

    format_version: int
    algorithm_version: int
    source_signature: list[dict[str, str]]
    fingerprint: str
    frame_cells: int
    tile_cells: int
    data_sha256: str


@dataclass(frozen=True, slots=True)
class ElevationFreshness:
    """The freshness of one elevation artifact against current source inputs."""

    algorithm_version: int
    input_signature: list[dict[str, str]] | None
    current: bool
    reason: str | None = None


def canonical_json(data: Any) -> str:
    """Format data into deterministic canonical UTF-8 JSON text."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def elevation_source_signature(
    continent_fingerprint: str,
    config_digest: str = DEFAULT_CONFIG_DIGEST,
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
) -> list[dict[str, str]]:
    """Return the sorted input identities and digests for elevation generation."""
    rows = [
        {"digest": str(algorithm_version), "identity": "algorithm_version"},
        {"digest": config_digest, "identity": "config"},
        {"digest": continent_fingerprint, "identity": "content/maps/continent.yaml"},
    ]
    return sorted(rows, key=lambda item: item["identity"])


def elevation_fingerprint(source_signature: Sequence[Mapping[str, str]]) -> str:
    """Compute the SHA-256 fingerprint over canonical source signature JSON."""
    signature_list = [
        {"digest": str(item["digest"]), "identity": str(item["identity"])}
        for item in source_signature
    ]
    sorted_signature = sorted(signature_list, key=lambda item: item["identity"])
    text = canonical_json(sorted_signature)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_data_sha256(
    tiles: Iterable[Mapping[str, Any]],
    frame_cells: int,
    tile_cells: int = ELEVATION_TILE_CELLS,
    version: int = ELEVATION_FORMAT_VERSION,
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
) -> str:
    """Compute SHA-256 over ordered tiles without raster expansion.

    Validates that:
    1. Tile count equals exactly ``ceil(frame_cells / tile_cells) ** 2``.
    2. Tiles appear in exact row-major order: ``ty`` 0..N-1, ``tx`` 0..N-1.
    3. Tile coordinates are valid integers (never booleans).
    4. Base64 strings decode successfully to valid compressed byte arrays.
    """
    if isinstance(frame_cells, bool) or not isinstance(frame_cells, int) or frame_cells <= 0:
        raise ElevationDocumentError(f"invalid frame_cells {frame_cells!r}")
    if isinstance(tile_cells, bool) or not isinstance(tile_cells, int) or tile_cells <= 0:
        raise ElevationDocumentError(f"invalid tile_cells {tile_cells!r}")

    num_tiles = math.ceil(frame_cells / tile_cells)
    expected_total = num_tiles * num_tiles

    hasher = hashlib.sha256()
    hasher.update(
        f"{version}:{algorithm_version}:{frame_cells}:{tile_cells}:{expected_total}:".encode(
            "ascii"
        )
    )

    count = 0
    for i, tile in enumerate(tiles):
        count += 1
        expected_ty = i // num_tiles
        expected_tx = i % num_tiles
        tx = tile.get("x")
        ty = tile.get("y")
        if isinstance(tx, bool) or not isinstance(tx, int) or tx != expected_tx:
            raise ElevationCorruptionError(
                f"tile {i} invalid x coordinate: expected {expected_tx}, got {tx!r}"
            )
        if isinstance(ty, bool) or not isinstance(ty, int) or ty != expected_ty:
            raise ElevationCorruptionError(
                f"tile {i} invalid y coordinate: expected {expected_ty}, got {ty!r}"
            )
        raw_data = tile.get("data")
        if not isinstance(raw_data, str):
            raise ElevationCorruptionError(f"tile ({tx}, {ty}) data must be a string")
        try:
            compressed = base64.b64decode(raw_data, validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise ElevationCorruptionError(
                f"tile ({tx}, {ty}) base64 decoding failed: {exc}"
            ) from exc

        hasher.update(f"{tx}:{ty}:{len(compressed)}:".encode("ascii"))
        hasher.update(compressed)

    if count != expected_total:
        raise ElevationCorruptionError(
            f"expected {expected_total} tiles ({num_tiles}x{num_tiles}), got {count}"
        )

    return hasher.hexdigest()


def _document(source: Mapping | str) -> Mapping:
    if isinstance(source, str):
        try:
            return json.loads(source)
        except json.JSONDecodeError as exc:
            raise ElevationDocumentError(f"invalid elevation JSON: {exc}") from exc
    return source


def read_elevation_metadata(source: Mapping | str) -> ElevationMetadata:
    """Read the artifact's metadata and signatures without expanding any raster."""
    doc = _document(source)
    version = doc.get("version")
    if isinstance(version, bool) or version != ELEVATION_FORMAT_VERSION:
        raise ElevationDocumentError(f"unsupported elevation version {version!r}")

    algorithm = doc.get("algorithm_version")
    if isinstance(algorithm, bool) or not isinstance(algorithm, int) or algorithm < 1:
        raise ElevationDocumentError("elevation algorithm_version is missing or invalid")

    frame_cells = doc.get("frame_cells")
    if isinstance(frame_cells, bool) or not isinstance(frame_cells, int) or frame_cells <= 0:
        raise ElevationDocumentError("frame_cells must be a positive integer")

    tile_cells = doc.get("tile_cells")
    if isinstance(tile_cells, bool) or tile_cells != ELEVATION_TILE_CELLS:
        raise ElevationDocumentError(f"tile_cells must be {ELEVATION_TILE_CELLS}")

    source_sig = doc.get("source_signature")
    if not isinstance(source_sig, list) or not source_sig:
        raise ElevationDocumentError("source_signature must be a non-empty list")
    for item in source_sig:
        if not isinstance(item, dict) or "identity" not in item or "digest" not in item:
            raise ElevationDocumentError("source_signature items must have identity and digest")

    fingerprint = doc.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ElevationDocumentError("fingerprint must be a non-empty string")

    data_sha256 = doc.get("data_sha256")
    if not isinstance(data_sha256, str) or not data_sha256:
        raise ElevationDocumentError("data_sha256 must be a non-empty string")

    return ElevationMetadata(
        format_version=version,
        algorithm_version=algorithm,
        source_signature=source_sig,
        fingerprint=fingerprint,
        frame_cells=frame_cells,
        tile_cells=tile_cells,
        data_sha256=data_sha256,
    )


def verify_elevation_data_integrity(
    document: Mapping | str,
    expected_frame_cells: int | None = None,
) -> ElevationMetadata:
    """Verify metadata, fingerprint and data_sha256 structure without raster expansion."""
    doc = _document(document)
    metadata = read_elevation_metadata(doc)

    if expected_frame_cells is not None and metadata.frame_cells != expected_frame_cells:
        raise ElevationDocumentError(
            f"frame_cells {metadata.frame_cells} does not match expected {expected_frame_cells}"
        )

    expected_fp = elevation_fingerprint(metadata.source_signature)
    if metadata.fingerprint != expected_fp:
        raise ElevationCorruptionError(
            f"fingerprint mismatch: artifact claims {metadata.fingerprint!r}, "
            f"computed {expected_fp!r}"
        )

    tiles = doc.get("tiles")
    if not isinstance(tiles, list):
        raise ElevationDocumentError("tiles must be a list")

    computed_sha256 = compute_data_sha256(
        tiles,
        frame_cells=metadata.frame_cells,
        tile_cells=metadata.tile_cells,
        version=metadata.format_version,
        algorithm_version=metadata.algorithm_version,
    )
    if computed_sha256 != metadata.data_sha256:
        raise ElevationCorruptionError(
            f"data_sha256 mismatch: artifact claims {metadata.data_sha256!r}, "
            f"computed {computed_sha256!r}"
        )

    return metadata


def elevation_freshness(
    metadata: ElevationMetadata,
    expected_source_signature: list[dict[str, str]],
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
) -> ElevationFreshness:
    """Compare metadata against expected inputs and report currency or specific reason."""
    if metadata.format_version != ELEVATION_FORMAT_VERSION:
        return ElevationFreshness(
            algorithm_version=metadata.algorithm_version,
            input_signature=metadata.source_signature,
            current=False,
            reason=f"unsupported format version {metadata.format_version!r}",
        )
    if metadata.algorithm_version != algorithm_version:
        return ElevationFreshness(
            algorithm_version=metadata.algorithm_version,
            input_signature=metadata.source_signature,
            current=False,
            reason=f"algorithm version {metadata.algorithm_version!r} is not supported",
        )

    # Compare signatures item by item to name the specific changed source
    meta_by_id = {item["identity"]: item["digest"] for item in metadata.source_signature}
    exp_by_id = {item["identity"]: item["digest"] for item in expected_source_signature}

    if meta_by_id != exp_by_id:
        mismatched = []
        for ident in sorted(set(meta_by_id) | set(exp_by_id)):
            if meta_by_id.get(ident) != exp_by_id.get(ident):
                mismatched.append(ident)
        changed_name = ", ".join(mismatched) if mismatched else "unknown"
        return ElevationFreshness(
            algorithm_version=metadata.algorithm_version,
            input_signature=metadata.source_signature,
            current=False,
            reason=f"stale (source {changed_name} changed)",
        )

    return ElevationFreshness(
        algorithm_version=metadata.algorithm_version,
        input_signature=metadata.source_signature,
        current=True,
    )


def encode_tile(
    bands: Any,
    tiers: Any,
    tx: int,
    ty: int,
    frame_cells: int,
    tile_cells: int = ELEVATION_TILE_CELLS,
) -> str:
    """Encode one 64x64 tile into canonical base64 zlib text."""
    tile_bytes = bytearray(tile_cells * tile_cells)
    has_shape = hasattr(bands, "shape")

    for ly in range(tile_cells):
        for lx in range(tile_cells):
            x = tx * tile_cells + lx
            y = ty * tile_cells + ly
            if x < frame_cells and y < frame_cells:
                b = int(bands[y, x] if has_shape else bands[y][x])
                t = int(tiers[y, x] if has_shape else tiers[y][x])
                byte_val = (b << 4) | (t & 0x03)
            else:
                byte_val = 0
            tile_bytes[ly * tile_cells + lx] = byte_val

    compressed = zlib.compress(bytes(tile_bytes), level=9)
    return base64.b64encode(compressed).decode("ascii")


def decode_tile(
    data_b64: str,
    tx: int,
    ty: int,
    frame_cells: int,
    tile_cells: int = ELEVATION_TILE_CELLS,
) -> bytes:
    """Decode one tile into exactly 4096 packed bytes, enforcing all integrity rules."""
    try:
        compressed = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ElevationTileCorruptionError(
            f"tile ({tx}, {ty}) base64 decoding failed: {exc}"
        ) from exc

    target_len = tile_cells * tile_cells
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(compressed, max_length=target_len)
        if len(decoded) != target_len:
            raise ElevationTileCorruptionError(
                f"tile ({tx}, {ty}) decompressed to {len(decoded)} bytes, expected {target_len}"
            )
        extra = decompressor.decompress(b"", max_length=1)
        if extra or decompressor.unconsumed_tail:
            raise ElevationTileCorruptionError(
                f"tile ({tx}, {ty}) exceeded {target_len}-byte output ceiling"
            )
        if decompressor.unused_data:
            raise ElevationTileCorruptionError(
                f"tile ({tx}, {ty}) has trailing unused data ({len(decompressor.unused_data)} bytes)"
            )
        if not decompressor.eof:
            raise ElevationTileCorruptionError(
                f"tile ({tx}, {ty}) incomplete stream did not reach end-of-file"
            )
    except (zlib.error, ValueError) as exc:
        if isinstance(exc, ElevationTileCorruptionError):
            raise
        raise ElevationTileCorruptionError(
            f"tile ({tx}, {ty}) decompression failed: {exc}"
        ) from exc

    # Nibble checks: bits 2 and 3 must be zero
    for idx, byte in enumerate(decoded):
        if byte & 0x0C != 0:
            raise ElevationTileCorruptionError(
                f"tile ({tx}, {ty}) cell {idx} has non-zero reserved bits: {byte:#04x}"
            )

    # Partial edge check: cells outside the frame must be zero
    num_tiles = math.ceil(frame_cells / tile_cells)
    if tx == num_tiles - 1 or ty == num_tiles - 1:
        for ly in range(tile_cells):
            for lx in range(tile_cells):
                gx = tx * tile_cells + lx
                gy = ty * tile_cells + ly
                if gx >= frame_cells or gy >= frame_cells:
                    idx = ly * tile_cells + lx
                    if decoded[idx] != 0:
                        raise ElevationTileCorruptionError(
                            f"tile ({tx}, {ty}) padding cell ({gx}, {gy}) is non-zero: {decoded[idx]}"
                        )

    return decoded


def encode_elevation_artifact(
    bands: Any,
    tiers: Any,
    frame_cells: int,
    continent_fingerprint: str,
    config_digest: str = DEFAULT_CONFIG_DIGEST,
    algorithm_version: int = ELEVATION_ALGORITHM_VERSION,
    tile_cells: int = ELEVATION_TILE_CELLS,
) -> str:
    """Encode rasters into the complete canonical JSON artifact text.

    Enforces the 4 MiB budget: raises ``ElevationBudgetExceededError`` before returning
    if the text exceeds ``MAX_ELEVATION_BYTES``.
    """
    num_tiles = math.ceil(frame_cells / tile_cells)
    tiles: list[dict[str, Any]] = []

    for ty in range(num_tiles):
        for tx in range(num_tiles):
            encoded = encode_tile(bands, tiers, tx, ty, frame_cells, tile_cells)
            tiles.append({"x": tx, "y": ty, "data": encoded})

    source_sig = elevation_source_signature(
        continent_fingerprint=continent_fingerprint,
        config_digest=config_digest,
        algorithm_version=algorithm_version,
    )
    fingerprint = elevation_fingerprint(source_sig)
    data_sha256 = compute_data_sha256(
        tiles,
        frame_cells=frame_cells,
        tile_cells=tile_cells,
        version=ELEVATION_FORMAT_VERSION,
        algorithm_version=algorithm_version,
    )

    doc = {
        "version": ELEVATION_FORMAT_VERSION,
        "algorithm_version": algorithm_version,
        "source_signature": source_sig,
        "fingerprint": fingerprint,
        "frame_cells": frame_cells,
        "tile_cells": tile_cells,
        "data_sha256": data_sha256,
        "tiles": tiles,
    }

    text = json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n"
    raw_len = len(text.encode("utf-8"))
    if raw_len > MAX_ELEVATION_BYTES:
        raise ElevationBudgetExceededError(
            f"elevation artifact is {raw_len} bytes, exceeds {MAX_ELEVATION_BYTES} (4 MiB) budget"
        )

    return text
