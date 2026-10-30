"""Offline deterministic elevation and prominence generation.

The generator owns the complete physical relief of the wilderness frame: the
land/sea base with a coastal rise, the summit-ridge mountain rise and river
carving, domain-warped multi-octave value noise, the authored ordered elevation
shapes, quantization to the sixteen elevation bands, and the ring-mean
prominence tiers with four-connected cluster suppression. It imports NumPy and
SciPy, which live in the package's ``generation`` extra; nothing on the runtime
path imports this module, and importing it never reaches game code.

Stages, in order:

1. Base geometry from one :class:`~elosern_map_core.terrain.TerrainDefinition`:
   land cells come from :func:`mainland_row_intervals`, inland water from
   ``waterway_cells``. The coastal rise is linear in the Euclidean distance to
   sea and capped; the mountain rise is the ridge-centre proximity across the
   authored corridor; river cells are carved and land is never negative.
2. Domain-warped fractal value noise. The lattice hash is an integer avalanche
   mix (xor shifts 16/15/16 with the MurmurHash3 finalizer multipliers
   ``0x7FEB352D``/``0x846CA68B`` and explicit uint32 overflow), so no
   coordinate-linear congruential stripes appear. Octaves combine with the
   configured lacunarity and persistence; every cell is scaled by its region
   amplitude (hills > open > coast).
3. The authored shapes apply strictly in declaration order. Their
   ``amount``/``target_band`` are authored in bands, so ``raise``/``lower``
   add or subtract ``amount`` bands weighted by the feather and ``flatten``
   blends towards ``target_band``; the band quantities are divided by the
   configuration's ``quantization_scale`` because quantization multiplies the
   raster by it, so an authored band keeps its meaning at the configured
   scale. ``no_prominence`` records a final override mask. The feather weight
   is 1 inside the shape and decreases linearly to 0 over ``feather`` cells
   outside it.
4. Fixed-configuration quantization to bands ``0..15``; sea returns to band 0
   and every river cell is clamped to its immediate land banks.
5. Ring-mean prominence becomes tiers ``0..3`` through the configured
   thresholds; sea, canopy (the two forest regions) and ``no_prominence`` cells
   are always tier 0, and four-connected components smaller than
   ``min_cluster_area`` are cleared.

Every seed, octave, wavelength, amplitude, radius, threshold and cluster
minimum belongs to the one immutable versioned :class:`ElevationConfig`. There
is no module-level mutable state, so two worlds can never share a raster or a
noise table.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from scipy import ndimage

from .documents import ElevationShapeDeclaration
from .schema import ELEVATION_OPS, ELEVATION_SHAPES
from .terrain import (
    TerrainDefinition,
    border_river_row,
    forest_edge_row,
    mainland_row_intervals,
    rasterize_segment,
    ridge_center_x,
)

#: Version of the generated-raster contract and its configuration shape.
ELEVATION_CONFIG_VERSION = 1

#: Highest elevation band (``bands`` is ``uint8`` over ``0..ELEVATION_BAND_MAX``).
ELEVATION_BAND_MAX = 15

#: Highest prominence tier (``tiers`` is ``uint8`` over ``0..PROMINENCE_TIER_MAX``).
PROMINENCE_TIER_MAX = 3

#: The two forest regions whose land is canopy: it never carries a tier.
CANOPY_REGIONS = frozenset({"north_deep_forest", "northwest_highland_forest"})

_SHAPE_KINDS = ELEVATION_SHAPES
_SHAPE_OPS = ELEVATION_OPS
_MISSING_BANK = 0x7FFF


def _int_field(value: object, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def _float_field(
    value: object, label: str, *, minimum: float, exclusive: bool = False
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    if number < minimum or (exclusive and number == minimum):
        comparison = "greater than" if exclusive else "at least"
        raise ValueError(f"{label} must be {comparison} {minimum}")
    return number


@dataclass(frozen=True, slots=True)
class ElevationConfig:
    """Every physical, noise, shape and prominence constant of the generator.

    The configuration is immutable and versioned: a caller passes the whole
    record explicitly, so a synthetic test can inject a small frame's known
    seed, wavelengths and thresholds without touching module state. Region
    amplitudes keep the design order ``hills > open > coast``.
    """

    version: int = ELEVATION_CONFIG_VERSION
    seed: int = 42
    coast_rise_rate: float = 0.05
    coast_max_rise: float = 6.0
    ridge_mountain_rise: float = 8.0
    river_carve_depth: float = 2.0
    noise_seed: int = 1337
    base_wavelength: float = 16.0
    octaves: int = 4
    persistence: float = 0.5
    lacunarity: float = 2.0
    warp_strength: float = 6.0
    warp_wavelength: float = 32.0
    amplitude_hills: float = 0.35
    amplitude_open: float = 0.18
    amplitude_coast: float = 0.08
    amplitude_mountains: float = 0.40
    amplitude_forest: float = 0.20
    quantization_scale: float = 1.0
    ring_inner_radius: int = 3
    ring_outer_radius: int = 8
    prominence_thresholds: tuple[float, float, float] = (1.0, 2.0, 3.0)
    min_cluster_area: int = 4

    def __post_init__(self) -> None:
        _int_field(self.version, "version", minimum=1)
        _int_field(self.seed, "seed", minimum=0)
        _int_field(self.noise_seed, "noise_seed", minimum=0)
        _int_field(self.octaves, "octaves", minimum=1)
        _int_field(self.ring_inner_radius, "ring_inner_radius", minimum=1)
        _int_field(self.ring_outer_radius, "ring_outer_radius", minimum=2)
        if self.ring_inner_radius >= self.ring_outer_radius:
            raise ValueError("ring_inner_radius must be below ring_outer_radius")
        _int_field(self.min_cluster_area, "min_cluster_area", minimum=1)
        _float_field(self.coast_rise_rate, "coast_rise_rate", minimum=0.0)
        _float_field(self.coast_max_rise, "coast_max_rise", minimum=0.0)
        _float_field(self.ridge_mountain_rise, "ridge_mountain_rise", minimum=0.0)
        _float_field(self.river_carve_depth, "river_carve_depth", minimum=0.0)
        _float_field(
            self.base_wavelength, "base_wavelength", minimum=0.0, exclusive=True
        )
        _float_field(self.persistence, "persistence", minimum=0.0, exclusive=True)
        _float_field(self.lacunarity, "lacunarity", minimum=1.0, exclusive=True)
        _float_field(self.warp_strength, "warp_strength", minimum=0.0)
        _float_field(
            self.warp_wavelength, "warp_wavelength", minimum=0.0, exclusive=True
        )
        _float_field(
            self.quantization_scale, "quantization_scale", minimum=0.0, exclusive=True
        )
        for name in (
            "amplitude_hills",
            "amplitude_open",
            "amplitude_coast",
            "amplitude_mountains",
            "amplitude_forest",
        ):
            _float_field(getattr(self, name), name, minimum=0.0)
        if not self.amplitude_hills > self.amplitude_open > self.amplitude_coast:
            raise ValueError(
                "region amplitudes must keep "
                "amplitude_hills > amplitude_open > amplitude_coast"
            )
        thresholds = self.prominence_thresholds
        if not isinstance(thresholds, tuple) or len(thresholds) != 3:
            raise ValueError("prominence_thresholds must be a tuple of three numbers")
        previous = -1.0
        for index, threshold in enumerate(thresholds):
            value = _float_field(
                threshold, f"prominence_thresholds[{index}]", minimum=0.0
            )
            if value <= previous:
                raise ValueError("prominence_thresholds must be strictly increasing")
            previous = value


#: The authored default configuration. Physical parameters are configuration,
#: never duplicated balance assertions.
DEFAULT_ELEVATION_CONFIG = ElevationConfig()


class ElevationRasters(NamedTuple):
    """The generated rasters, indexed ``[y, x]`` over the wilderness frame.

    ``bands`` are ``uint8`` elevation bands ``0..15`` (sea is exactly 0);
    ``tiers`` are ``uint8`` prominence tiers ``0..3``. Both arrays are
    read-only and belong to the returned value, never to module state.
    """

    bands: np.ndarray
    tiers: np.ndarray


# -- integer lattice noise ---------------------------------------------------


def _hash01(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    """Deterministic ``[0, 1)`` avalanche hash of one integer lattice cell."""

    with np.errstate(over="ignore"):
        hashed = (
            (ix.astype(np.int64) & 0xFFFFFFFF).astype(np.uint32)
            * np.uint32(0x9E3779B1)
            + (iy.astype(np.int64) & 0xFFFFFFFF).astype(np.uint32)
            * np.uint32(0x85EBCA77)
            + np.uint32(seed & 0xFFFFFFFF)
        )
        hashed ^= hashed >> 16
        hashed *= np.uint32(0x7FEB352D)
        hashed ^= hashed >> 15
        hashed *= np.uint32(0x846CA68B)
        hashed ^= hashed >> 16
    return hashed.astype(np.float64) * (1.0 / 4294967296.0)


def _value_noise(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """Smoothstep-interpolated value noise sampled at continuous coordinates."""

    ix = np.floor(x).astype(np.int32)
    iy = np.floor(y).astype(np.int32)
    fx = x - ix
    fy = y - iy
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)

    top = _hash01(ix, iy, seed)
    corner = _hash01(ix + 1, iy, seed)
    top += (corner - top) * u

    bottom = _hash01(ix, iy + 1, seed)
    corner = _hash01(ix + 1, iy + 1, seed)
    bottom += (corner - bottom) * u

    return top + (bottom - top) * v


def _frame_size(width: object, height: object) -> tuple[int, int]:
    return (
        _int_field(width, "width", minimum=1),
        _int_field(height, "height", minimum=1),
    )


def fractal_noise(
    width: int,
    height: int,
    config: ElevationConfig = DEFAULT_ELEVATION_CONFIG,
) -> np.ndarray:
    """The domain-warped multi-octave value-noise field, ``[y, x]`` in ``[-1, 1]``.

    Domain warping perturbs the sample coordinate by a signed noise field at
    ``warp_wavelength``; the octaves then combine with the configured
    ``lacunarity``/``persistence`` and are normalised to zero mean. ``seed`` is
    the generator's master seed and ``noise_seed`` offsets the noise domain, so
    both participate. This stage is exposed so a focused assertion can measure
    directional residual autocorrelation without coastline or ridge trends.
    """

    width, height = _frame_size(width, height)
    if not isinstance(config, ElevationConfig):
        raise TypeError("config must be an ElevationConfig")

    base_seed = config.seed + config.noise_seed
    ys, xs = np.mgrid[0:height, 0:width]
    x = xs.astype(np.float64)
    y = ys.astype(np.float64)

    if config.warp_strength != 0.0:
        warp_x = (
            _value_noise(
                x / config.warp_wavelength,
                y / config.warp_wavelength,
                base_seed + 7919,
            )
            - 0.5
        ) * 2.0
        warp_y = (
            _value_noise(
                x / config.warp_wavelength,
                y / config.warp_wavelength,
                base_seed + 104729,
            )
            - 0.5
        ) * 2.0
        x = x + config.warp_strength * warp_x
        y = y + config.warp_strength * warp_y

    total = np.zeros((height, width), dtype=np.float64)
    amplitude = 1.0
    wavelength = config.base_wavelength
    normaliser = 0.0
    for octave in range(config.octaves):
        total += amplitude * _value_noise(
            x / wavelength, y / wavelength, base_seed + octave * 131
        )
        normaliser += amplitude
        amplitude *= config.persistence
        wavelength /= config.lacunarity
    return (total / normaliser - 0.5) * 2.0


# -- terrain rasters ---------------------------------------------------------


def _land_mask(terrain: TerrainDefinition) -> np.ndarray:
    frame = terrain.frame_cells
    land = np.zeros((frame, frame), dtype=bool)
    for y in range(frame):
        for low, high in mainland_row_intervals(terrain, y):
            land[y, low : high + 1] = True
    return land


def _river_mask(terrain: TerrainDefinition) -> np.ndarray:
    frame = terrain.frame_cells
    river = np.zeros((frame, frame), dtype=bool)
    for x, y in terrain.waterway_cells:
        if 0 <= x < frame and 0 <= y < frame:
            river[y, x] = True
    return river


def _column_rows(function, terrain: TerrainDefinition) -> np.ndarray:
    return np.array(
        [function(terrain, x) for x in range(terrain.frame_cells)], dtype=np.int64
    )[None, :]


def _row_centres(terrain: TerrainDefinition) -> np.ndarray:
    return np.array(
        [ridge_center_x(terrain, y) for y in range(terrain.frame_cells)],
        dtype=np.int64,
    )[:, None]


def _region_masks(terrain: TerrainDefinition) -> tuple[np.ndarray, ...]:
    """Disjoint masks for the seven terrain regions, mirroring the classifier.

    The vectorised mirrors are asserted equal to
    :func:`region_for_coordinates` on synthetic frames, so a change to the
    classifier cannot silently drift the elevation amplitudes or canopy mask.
    """

    frame = terrain.frame_cells
    ys, xs = np.mgrid[0:frame, 0:frame]
    forest_rows = _column_rows(forest_edge_row, terrain)
    river_rows = _column_rows(border_river_row, terrain)
    centres = _row_centres(terrain)
    coast = ys <= terrain.coastal_y_max

    north_deep_forest = ys >= forest_rows
    mountains = ~north_deep_forest & (
        np.abs(xs - centres) <= terrain.mountain_corridor_half_width
    )
    east = ~north_deep_forest & ~mountains & (xs > centres)
    west = ~north_deep_forest & ~mountains & (xs < centres)
    southeast_coast = east & coast
    eastern_plains = east & ~coast
    southwest_coast = west & coast
    northwest = west & ~coast & (ys > river_rows)
    western_hills = west & ~coast & (ys <= river_rows)
    return (
        north_deep_forest,
        northwest,
        mountains,
        western_hills,
        eastern_plains,
        southeast_coast,
        southwest_coast,
    )


def _region_amplitude_grid(
    terrain: TerrainDefinition, config: ElevationConfig
) -> np.ndarray:
    (
        north_deep_forest,
        northwest,
        mountains,
        western_hills,
        eastern_plains,
        southeast_coast,
        southwest_coast,
    ) = _region_masks(terrain)
    amplitudes = np.full(
        (terrain.frame_cells, terrain.frame_cells),
        config.amplitude_open,
        dtype=np.float64,
    )
    amplitudes[north_deep_forest | northwest] = config.amplitude_forest
    amplitudes[mountains] = config.amplitude_mountains
    amplitudes[western_hills] = config.amplitude_hills
    amplitudes[eastern_plains] = config.amplitude_open
    amplitudes[southeast_coast | southwest_coast] = config.amplitude_coast
    return amplitudes


def region_amplitudes(
    terrain: TerrainDefinition,
    config: ElevationConfig = DEFAULT_ELEVATION_CONFIG,
) -> np.ndarray:
    """The region noise amplitude of every cell, ``float64`` ``[y, x]``.

    ``north_deep_forest`` and ``northwest_highland_forest`` share the forest
    amplitude, the mountain corridor takes the mountain amplitude, and the
    remaining regions keep ``hills > open > coast``.
    """

    if not isinstance(terrain, TerrainDefinition):
        raise TypeError("terrain must be a TerrainDefinition")
    if not isinstance(config, ElevationConfig):
        raise TypeError("config must be an ElevationConfig")
    return _region_amplitude_grid(terrain, config)


def _canopy_mask(terrain: TerrainDefinition, land: np.ndarray) -> np.ndarray:
    north_deep_forest, northwest, *_ = _region_masks(terrain)
    return land & (north_deep_forest | northwest)


def _base_elevation(
    terrain: TerrainDefinition,
    land: np.ndarray,
    river: np.ndarray,
    config: ElevationConfig,
) -> np.ndarray:
    coast = np.minimum(
        ndimage.distance_transform_edt(land) * config.coast_rise_rate,
        config.coast_max_rise,
    )
    frame = terrain.frame_cells
    xs = np.arange(frame, dtype=np.float64)[None, :]
    centres = _row_centres(terrain)
    half_width = terrain.mountain_corridor_half_width
    if half_width > 0:
        proximity = np.maximum(0.0, 1.0 - np.abs(xs - centres) / float(half_width))
    else:
        proximity = (xs == centres).astype(np.float64)
    elevation = coast + proximity * config.ridge_mountain_rise
    elevation[river] -= config.river_carve_depth
    np.maximum(elevation, 0.0, out=elevation)
    elevation[~land] = 0.0
    return elevation


# -- ordered feathered shapes ------------------------------------------------


def _shape_feather(shape: ElevationShapeDeclaration) -> int:
    return 0 if shape.feather is None else shape.feather


def _validate_shape(shape: ElevationShapeDeclaration) -> None:
    if not isinstance(shape, ElevationShapeDeclaration):
        raise TypeError("every shape must be an ElevationShapeDeclaration")
    if shape.shape not in _SHAPE_KINDS:
        raise ValueError(f"unknown elevation shape {shape.shape!r}")
    if shape.op not in _SHAPE_OPS:
        raise ValueError(f"unknown elevation shape op {shape.op!r}")
    if shape.shape == "circle":
        if shape.centre is None or shape.radius is None:
            raise ValueError("a circle shape needs a centre and a radius")
        _int_field(shape.centre[0], "circle centre x", minimum=0)
        _int_field(shape.centre[1], "circle centre y", minimum=0)
        _int_field(shape.radius, "circle radius", minimum=1)
    else:
        if len(shape.vertices) < 3:
            raise ValueError("a polygon shape needs at least three vertices")
        for index, vertex in enumerate(shape.vertices):
            _int_field(vertex[0], f"polygon vertex {index} x", minimum=0)
            _int_field(vertex[1], f"polygon vertex {index} y", minimum=0)
    if shape.op in ("raise", "lower"):
        if shape.amount is None:
            raise ValueError(f"a {shape.op} shape needs an amount")
        _int_field(shape.amount, f"{shape.op} amount", minimum=1)
    elif shape.op == "flatten":
        if shape.target_band is None:
            raise ValueError("a flatten shape needs a target_band")
        target = _int_field(shape.target_band, "flatten target_band", minimum=0)
        if target > ELEVATION_BAND_MAX:
            raise ValueError(
                f"flatten target_band must be at most {ELEVATION_BAND_MAX}"
            )
    if shape.op == "no_prominence":
        if shape.feather is not None:
            raise ValueError("a no_prominence shape must not declare a feather")
    elif shape.feather is not None:
        _int_field(shape.feather, "feather", minimum=1)


def _shape_assets(
    shape: ElevationShapeDeclaration, width: int, height: int
) -> tuple[int, int, int, int, np.ndarray, np.ndarray] | None:
    """``(left, top, right, bottom, inside, weight)`` clipped to the frame."""

    feather = _shape_feather(shape)

    if shape.shape == "circle":
        centre_x, centre_y = shape.centre  # type: ignore[misc]
        radius = shape.radius  # type: ignore[assignment]
        left = max(0, centre_x - radius - feather)
        right = min(width - 1, centre_x + radius + feather)
        top = max(0, centre_y - radius - feather)
        bottom = min(height - 1, centre_y + radius + feather)
        if left > right or top > bottom:
            return None
        ys, xs = np.mgrid[top : bottom + 1, left : right + 1]
        distance = np.hypot(xs - centre_x, ys - centre_y)
        inside = distance <= radius
        if feather > 0:
            weight = np.where(
                inside, 1.0, np.maximum(0.0, 1.0 - (distance - radius) / feather)
            )
        else:
            weight = inside.astype(np.float64)
        return left, top, right, bottom, inside, weight

    vertex_x = [vertex[0] for vertex in shape.vertices]
    vertex_y = [vertex[1] for vertex in shape.vertices]
    left = max(0, min(vertex_x) - feather)
    right = min(width - 1, max(vertex_x) + feather)
    top = max(0, min(vertex_y) - feather)
    bottom = min(height - 1, max(vertex_y) + feather)
    if left > right or top > bottom:
        return None

    ys = np.arange(top, bottom + 1, dtype=np.float64)[:, None]
    xs = np.arange(left, right + 1, dtype=np.float64)[None, :]
    inside = np.zeros((bottom - top + 1, right - left + 1), dtype=bool)
    edges = list(zip(shape.vertices, shape.vertices[1:] + shape.vertices[:1]))
    for (start_x, start_y), (end_x, end_y) in edges:
        if start_y == end_y:
            continue
        crosses = (start_y > ys) != (end_y > ys)
        crossing_x = (end_x - start_x) * (ys - start_y) / (end_y - start_y) + start_x
        inside ^= crosses & (xs < crossing_x)
    # A lattice cell on an edge belongs to the shape's interior.
    for start, end in edges:
        for cell_x, cell_y in rasterize_segment(start, end):
            if left <= cell_x <= right and top <= cell_y <= bottom:
                inside[cell_y - top, cell_x - left] = True

    if feather == 0:
        weight = inside.astype(np.float64)
    elif inside.all():
        weight = np.ones(inside.shape, dtype=np.float64)
    elif not inside.any():
        weight = np.zeros(inside.shape, dtype=np.float64)
    else:
        outside_distance = ndimage.distance_transform_edt(~inside)
        weight = np.where(
            inside, 1.0, np.maximum(0.0, 1.0 - outside_distance / feather)
        )
    return left, top, right, bottom, inside, weight


def shape_weight(
    shape: ElevationShapeDeclaration, width: int, height: int
) -> np.ndarray:
    """The feathered weight of one shape over a ``width`` by ``height`` frame.

    The weight is exactly 1 inside the shape (a lattice cell on an edge is
    inside) and decreases linearly to 0 over ``feather`` cells outside it. A
    ``no_prominence`` shape has no feather and returns its hard inside mask.
    This stage is exposed so a focused assertion can measure the gradient.
    """

    width, height = _frame_size(width, height)
    _validate_shape(shape)
    weight = np.zeros((height, width), dtype=np.float64)
    assets = _shape_assets(shape, width, height)
    if assets is None:
        return weight
    left, top, right, bottom, _inside, local = assets
    weight[top : bottom + 1, left : right + 1] = local
    return weight


def _apply_shape(
    elevation: np.ndarray,
    no_prominence_mask: np.ndarray,
    shape: ElevationShapeDeclaration,
    quantization_scale: float,
) -> None:
    """Apply one authored shape, whose ``amount``/``target_band`` are in bands.

    The raster holds unquantized elevation units, which quantization later
    multiplies by ``quantization_scale`` to obtain bands, so the authored band
    quantities are divided by that scale to express them in the raster's own
    units: an authored band stays one band at the configured scale instead of
    being multiplied by it.
    """

    height, width = elevation.shape
    assets = _shape_assets(shape, width, height)
    if assets is None:
        return
    left, top, right, bottom, inside, weight = assets
    region = elevation[top : bottom + 1, left : right + 1]
    if shape.op == "raise":
        region += (shape.amount or 0) / quantization_scale * weight
    elif shape.op == "lower":
        np.maximum(
            region - (shape.amount or 0) / quantization_scale * weight,
            0.0,
            out=region,
        )
    elif shape.op == "flatten":
        target = (shape.target_band or 0) / quantization_scale
        region[:] = (1.0 - weight) * region + weight * target
    elif shape.op == "no_prominence":
        no_prominence_mask[top : bottom + 1, left : right + 1] |= inside
    else:  # pragma: no cover - _validate_shape already rejected it
        raise ValueError(f"unknown elevation shape op {shape.op!r}")


# -- quantization and river postcondition ------------------------------------


def _quantize(
    elevation: np.ndarray, land: np.ndarray, config: ElevationConfig
) -> np.ndarray:
    scaled = np.floor(elevation * config.quantization_scale)
    bands = np.clip(scaled, 0.0, float(ELEVATION_BAND_MAX)).astype(np.uint8)
    bands[~land] = 0
    return bands


def _min_over_offsets(
    values: np.ndarray, offsets: tuple[tuple[int, int], ...], sentinel: int
) -> np.ndarray:
    result = np.full(values.shape, sentinel, dtype=values.dtype)
    height, width = values.shape
    for delta_x, delta_y in offsets:
        destination_y = slice(max(0, -delta_y), height - max(0, delta_y))
        source_y = slice(max(0, delta_y), height - max(0, -delta_y))
        destination_x = slice(max(0, -delta_x), width - max(0, delta_x))
        source_x = slice(max(0, delta_x), width - max(0, -delta_x))
        np.minimum(
            result[destination_y, destination_x],
            values[source_y, source_x],
            out=result[destination_y, destination_x],
        )
    return result


_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _apply_river_banks(
    bands: np.ndarray, land: np.ndarray, river: np.ndarray
) -> None:
    """Clamp every river cell to its immediate land banks (four-connected first).

    A river cell with no four-connected land bank falls back to the
    eight-connected neighbours; a cell with no land bank at all (a mouth on the
    sea) stays at its sea band of 0.
    """

    banks = land & ~river
    if not river.any() or not banks.any():
        return
    values = np.where(banks, bands.astype(np.int16), np.int16(_MISSING_BANK))
    minimum = _min_over_offsets(values, _ORTHOGONAL, _MISSING_BANK)
    missing = minimum == _MISSING_BANK
    if missing.any():
        diagonal = _min_over_offsets(values, _DIAGONAL, _MISSING_BANK)
        minimum = np.where(missing, diagonal, minimum)
    has_bank = river & (minimum < _MISSING_BANK)
    if has_bank.any():
        bands[has_bank] = np.minimum(
            bands[has_bank].astype(np.int16), minimum[has_bank]
        ).astype(np.uint8)


# -- prominence tiers --------------------------------------------------------


def _annulus_kernel(config: ElevationConfig) -> np.ndarray:
    outer = config.ring_outer_radius
    coords = np.arange(-outer, outer + 1, dtype=np.float64)
    delta_y, delta_x = np.meshgrid(coords, coords, indexing="ij")
    squared = delta_x * delta_x + delta_y * delta_y
    inner = float(config.ring_inner_radius)
    return (
        (squared > inner * inner) & (squared <= float(outer * outer))
    ).astype(np.float64)


def _prominence_tiers(
    bands: np.ndarray,
    land: np.ndarray,
    canopy: np.ndarray,
    no_prominence: np.ndarray,
    config: ElevationConfig,
) -> np.ndarray:
    kernel = _annulus_kernel(config)
    land_float = land.astype(np.float64)
    counts = ndimage.convolve(land_float, kernel, mode="constant", cval=0.0)
    values = ndimage.convolve(
        bands.astype(np.float64) * land_float, kernel, mode="constant", cval=0.0
    )
    ring_mean = np.zeros_like(values)
    np.divide(values, counts, out=ring_mean, where=counts > 0)
    prominence = bands.astype(np.float64) - ring_mean
    prominence[counts <= 0] = 0.0

    tiers = np.zeros(bands.shape, dtype=np.uint8)
    for level, threshold in enumerate(config.prominence_thresholds, start=1):
        tiers[prominence >= threshold] = level

    forced_zero = ~land | canopy | no_prominence
    tiers[forced_zero] = 0

    labels, component_count = ndimage.label(tiers > 0)
    if component_count:
        areas = np.bincount(labels.ravel())
        suppress = areas < config.min_cluster_area
        suppress[0] = False
        if suppress.any():
            tiers[suppress[labels]] = 0

    # ``no_prominence`` is the final override; canopy and sea stay tier 0.
    tiers[forced_zero] = 0
    return tiers


# -- public entry point ------------------------------------------------------


def generate_elevation(
    terrain: TerrainDefinition,
    shapes: Sequence[ElevationShapeDeclaration],
    config: ElevationConfig = DEFAULT_ELEVATION_CONFIG,
) -> ElevationRasters:
    """Generate the deterministic elevation bands and prominence tiers.

    ``terrain`` supplies the frame, mainland polygon, coastal band, ridge,
    waterways and forest edge; ``shapes`` apply strictly in the declared
    order; ``config`` owns every parameter. The result is indexed ``[y, x]``:
    ``bands`` are ``uint8`` elevation bands ``0..15`` (sea exactly 0) and
    ``tiers`` are ``uint8`` prominence tiers ``0..3``. Identical inputs return
    identical bytes; both arrays are read-only.
    """

    if not isinstance(terrain, TerrainDefinition):
        raise TypeError("terrain must be a TerrainDefinition")
    if not isinstance(config, ElevationConfig):
        raise TypeError("config must be an ElevationConfig")
    shape_list = tuple(shapes)
    for shape in shape_list:
        _validate_shape(shape)

    frame = terrain.frame_cells
    land = _land_mask(terrain)
    river = _river_mask(terrain)
    elevation = _base_elevation(terrain, land, river, config)
    elevation += fractal_noise(frame, frame, config) * _region_amplitude_grid(
        terrain, config
    )
    np.maximum(elevation, 0.0, out=elevation)

    no_prominence = np.zeros((frame, frame), dtype=bool)
    for shape in shape_list:
        _apply_shape(elevation, no_prominence, shape, config.quantization_scale)
    elevation[~land] = 0.0

    bands = _quantize(elevation, land, config)
    _apply_river_banks(bands, land, river)
    canopy = _canopy_mask(terrain, land)
    tiers = _prominence_tiers(bands, land, canopy, no_prominence, config)

    bands.setflags(write=False)
    tiers.setflags(write=False)
    return ElevationRasters(bands=bands, tiers=tiers)


__all__ = [
    "CANOPY_REGIONS",
    "DEFAULT_ELEVATION_CONFIG",
    "ELEVATION_BAND_MAX",
    "ELEVATION_CONFIG_VERSION",
    "ElevationConfig",
    "ElevationRasters",
    "PROMINENCE_TIER_MAX",
    "fractal_noise",
    "generate_elevation",
    "region_amplitudes",
    "shape_weight",
]
