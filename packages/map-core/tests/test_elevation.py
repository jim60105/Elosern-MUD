"""Mechanism tests for deterministic offline elevation and prominence generation.

Every physical assertion runs on small synthetic frames with injected known
configs, so no shipped geography, raster snapshot or authored wording is
pinned. The directional autocorrelation test measures the residual noise field
itself, excluding coastline and ridge trends by construction.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from elosern_map_core.documents import ElevationShapeDeclaration
from elosern_map_core.elevation import (
    CANOPY_REGIONS,
    DEFAULT_ELEVATION_CONFIG,
    ELEVATION_BAND_MAX,
    ELEVATION_CONFIG_VERSION,
    PROMINENCE_TIER_MAX,
    fractal_noise,
    generate_elevation,
    region_amplitudes,
    shape_weight,
)
from elosern_map_core.terrain import (
    REGION_KEYS,
    TerrainDefinition,
    is_land_cell,
    region_for_coordinates,
    ridge_center_x,
)

_FRAME = 64


def _flavors() -> dict[str, tuple[str, ...]]:
    return {key: (key,) for key in REGION_KEYS}


def synthetic_terrain(frame_cells: int = _FRAME) -> TerrainDefinition:
    """One deterministic frame with land, sea, ridge, river, canopy and coast."""

    north = frame_cells * 3 // 4
    forest_row = frame_cells * 5 // 8
    river_row = frame_cells // 2
    ridge_x = frame_cells // 2
    return TerrainDefinition(
        frame_cells=frame_cells,
        mainland_boundary_km=(
            (0, 0),
            (frame_cells, 0),
            (frame_cells, north),
            (0, north),
        ),
        forest_edge=((0, forest_row), (frame_cells - 1, forest_row)),
        waterway_routes={
            "border_river": ((frame_cells // 3, river_row), (0, river_row))
        },
        waterway_fords={},
        border_river_key="border_river",
        ridge_base_x=ridge_x,
        ridge_period=7,
        ridge_step=1,
        ridge_min_x=0,
        ridge_max_x=frame_cells - 1,
        ridge_north_limit=frame_cells - 1,
        ridge_passes=((0, 1),),
        coastal_y_max=frame_cells * 3 // 20,
        mountain_corridor_half_width=2,
        region_flavors=_flavors(),
    )


def _background(terrain: TerrainDefinition) -> ElevationShapeDeclaration:
    last = terrain.frame_cells - 1
    return ElevationShapeDeclaration(
        shape="polygon",
        op="flatten",
        vertices=((0, 0), (last, 0), (last, last), (0, last)),
        feather=1,
        target_band=1,
    )


def _circle(
    op: str,
    x: int,
    y: int,
    radius: int,
    *,
    feather: int | None = 1,
    amount: int | None = None,
    target_band: int | None = None,
) -> ElevationShapeDeclaration:
    return ElevationShapeDeclaration(
        shape="circle",
        op=op,
        centre=(x, y),
        radius=radius,
        amount=amount,
        target_band=target_band,
        feather=None if op == "no_prominence" else feather,
    )


def _disc_mask(centre_x: int, centre_y: int, radius: int, frame: int) -> np.ndarray:
    ys, xs = np.mgrid[0:frame, 0:frame]
    return (xs - centre_x) ** 2 + (ys - centre_y) ** 2 <= radius * radius


def _lag_correlation(field: np.ndarray, delta_x: int, delta_y: int) -> float:
    """Pearson correlation of the field with itself at one signed lag pair."""

    height, width = field.shape
    first = field
    second = field
    if delta_y > 0:
        first = first[: height - delta_y, :]
        second = second[delta_y:, :]
    elif delta_y < 0:
        first = first[-delta_y:, :]
        second = second[: height + delta_y, :]
    if delta_x > 0:
        first = first[:, : width - delta_x]
        second = second[:, delta_x:]
    elif delta_x < 0:
        first = first[:, -delta_x:]
        second = second[:, : width + delta_x]
    first = first - first.mean()
    second = second - second.mean()
    denominator = float(np.sqrt((first * first).sum() * (second * second).sum()))
    if denominator == 0.0:
        return 0.0
    return float((first * second).sum() / denominator)


def test_repeat_generation_is_byte_identical():
    terrain = synthetic_terrain()
    shapes = [
        _background(terrain),
        _circle("flatten", 10, 12, 2, target_band=9),
    ]

    first = generate_elevation(terrain, shapes)
    second = generate_elevation(terrain, shapes)

    assert first.bands.tobytes() == second.bands.tobytes()
    assert first.tiers.tobytes() == second.tiers.tobytes()
    bands, tiers = first
    assert bands is first.bands
    assert tiers is first.tiers


def test_rasters_are_bounded_uint8_and_read_only():
    result = generate_elevation(synthetic_terrain(), ())

    assert result.bands.dtype == np.uint8
    assert result.tiers.dtype == np.uint8
    assert result.bands.shape == (_FRAME, _FRAME)
    assert result.tiers.shape == (_FRAME, _FRAME)
    assert int(result.bands.max()) <= ELEVATION_BAND_MAX
    assert int(result.tiers.max()) <= PROMINENCE_TIER_MAX
    assert not result.bands.flags.writeable
    assert not result.tiers.flags.writeable
    with pytest.raises(ValueError):
        result.bands[0, 0] = 1


def test_sea_is_band_zero_and_tier_zero():
    terrain = synthetic_terrain()
    sea_start = terrain.frame_cells * 3 // 4  # the mainland boundary's north edge
    result = generate_elevation(
        terrain,
        [
            _background(terrain),
            _circle("flatten", 10, 12, 2, target_band=12),
        ],
    )

    assert np.all(result.bands[sea_start:, :] == 0)
    assert np.all(result.tiers[sea_start:, :] == 0)


def test_ridge_centre_exceeds_adjacent_lowlands():
    terrain = synthetic_terrain()
    result = generate_elevation(terrain, ())
    row = 12  # below the forest edge and clear of the river row
    centre = ridge_center_x(terrain, row)

    assert result.bands[row, centre] > result.bands[row, centre - 2]
    assert result.bands[row, centre] > result.bands[row, centre + 2]


def test_river_never_exceeds_immediate_land_banks():
    terrain = synthetic_terrain()
    result = generate_elevation(
        terrain,
        [
            _background(terrain),
            _circle("raise", 10, 32, 1, amount=5),
        ],
    )
    bands = result.bands
    river = terrain.waterway_cells
    cardinal = ((1, 0), (-1, 0), (0, 1), (0, -1))
    diagonal = ((1, 1), (1, -1), (-1, 1), (-1, -1))

    def banks_of(cell, offsets):
        x, y = cell
        found = []
        for delta_x, delta_y in offsets:
            neighbour = (x + delta_x, y + delta_y)
            if (
                0 <= neighbour[0] < terrain.frame_cells
                and 0 <= neighbour[1] < terrain.frame_cells
                and neighbour not in river
                and is_land_cell(terrain, neighbour)
            ):
                found.append(neighbour)
        return found

    checked = 0
    for cell in river:
        banks = banks_of(cell, cardinal) or banks_of(cell, diagonal)
        if not banks:
            continue
        checked += 1
        limit = min(int(bands[bank_y, bank_x]) for bank_x, bank_y in banks)
        assert int(bands[cell[1], cell[0]]) <= limit

    assert checked > 0
    assert max(int(bands[y, x]) for x, y in river) > 0


def test_canopy_and_no_prominence_cells_never_carry_a_tier():
    terrain = synthetic_terrain()
    canopy_bump = _circle("flatten", 10, 44, 2, target_band=12)
    plain_bump = _circle("flatten", 40, 12, 2, target_band=12)
    no_prominence = _circle("no_prominence", 40, 12, 2)
    control = _circle("flatten", 58, 12, 2, target_band=12)
    result = generate_elevation(
        terrain,
        [_background(terrain), canopy_bump, plain_bump, no_prominence, control],
    )

    canopy = np.zeros((_FRAME, _FRAME), dtype=bool)
    for y in range(_FRAME):
        for x in range(_FRAME):
            canopy[y, x] = region_for_coordinates(terrain, x, y) in CANOPY_REGIONS

    assert np.all(result.tiers[canopy] == 0)
    assert np.all(result.tiers[_disc_mask(40, 12, 2, _FRAME)] == 0)
    assert result.tiers[44, 10] == 0
    assert result.tiers[12, 40] == 0
    # The same raised disc outside canopy and no_prominence stays prominent.
    assert result.tiers[12, 58] > 0
    assert np.all(result.tiers[_disc_mask(58, 12, 2, _FRAME)] > 0)


def test_shapes_apply_in_declared_order_and_accumulate():
    terrain = synthetic_terrain()
    background = _background(terrain)
    wide = _circle("flatten", 10, 10, 2, target_band=8)
    narrow = _circle("flatten", 10, 10, 1, target_band=2)

    wide_then_narrow = generate_elevation(terrain, [background, wide, narrow])
    assert wide_then_narrow.bands[10, 10] == 2
    assert wide_then_narrow.bands[12, 10] == 8  # inside wide, outside narrow

    narrow_then_wide = generate_elevation(terrain, [background, narrow, wide])
    assert narrow_then_wide.bands[10, 10] == 8

    raised = generate_elevation(
        terrain,
        [
            background,
            _circle("raise", 10, 10, 2, amount=3),
            _circle("raise", 10, 10, 2, amount=2),
        ],
    )
    assert raised.bands[10, 10] == 6

    raised_then_lowered = generate_elevation(
        terrain,
        [
            background,
            _circle("raise", 10, 10, 2, amount=3),
            _circle("lower", 10, 10, 2, amount=1),
        ],
    )
    assert raised_then_lowered.bands[10, 10] == 3


def test_circle_and_polygon_feather_weights_decrease_linearly():
    circle = _circle("raise", 10, 10, 3, feather=4, amount=1)
    circle_weight = shape_weight(circle, 32, 32)

    assert circle_weight[10, 10] == 1.0
    assert circle_weight[10, 13] == 1.0  # the radius itself is interior
    assert circle_weight[10, 14] == pytest.approx(0.75)
    assert circle_weight[10, 15] == pytest.approx(0.5)
    assert circle_weight[10, 16] == pytest.approx(0.25)
    assert circle_weight[10, 17] == 0.0
    assert circle_weight[10, 20] == 0.0

    polygon = ElevationShapeDeclaration(
        shape="polygon",
        op="raise",
        vertices=((2, 2), (10, 2), (10, 10), (2, 10)),
        amount=1,
        feather=3,
    )
    polygon_weight = shape_weight(polygon, 16, 16)

    assert polygon_weight[6, 6] == 1.0
    assert polygon_weight[6, 2] == 1.0  # a lattice cell on the edge is interior
    assert polygon_weight[6, 10] == 1.0
    assert polygon_weight[6, 11] == pytest.approx(1.0 - 1 / 3)
    assert polygon_weight[6, 12] == pytest.approx(1.0 - 2 / 3)
    assert polygon_weight[6, 13] == 0.0


def test_ring_prominence_thresholds_map_to_tiers():
    terrain = synthetic_terrain()
    bumps = [
        _circle("flatten", 8, 12, 1, target_band=1),
        _circle("flatten", 28, 12, 1, target_band=2),
        _circle("flatten", 48, 12, 1, target_band=3),
        _circle("flatten", 48, 36, 1, target_band=10),
    ]
    result = generate_elevation(terrain, [_background(terrain), *bumps])

    # Background band 1, so each centre's ring mean is exactly 1.0.
    assert result.bands[12, 8] == 1
    assert result.bands[12, 28] == 2
    assert result.bands[12, 48] == 3
    assert result.bands[36, 48] == 10

    # Prominence 0, 1, 2 and 9 against the (1, 2, 3) thresholds.
    assert result.tiers[12, 8] == 0
    assert result.tiers[12, 28] == 1
    assert result.tiers[12, 48] == 2
    assert result.tiers[36, 48] == 3


def test_minimum_cluster_area_suppresses_tiny_components_and_keeps_large():
    terrain = synthetic_terrain()
    background = _background(terrain)
    tiny = _circle("flatten", 8, 12, 1, target_band=10)
    large = _circle("flatten", 48, 12, 2, target_band=10)
    # A radius-one feather contributes a nine-cell four-connected component
    # (centre, four cardinals, four diagonals); a radius-two disc is larger.
    config = replace(DEFAULT_ELEVATION_CONFIG, min_cluster_area=10)

    result = generate_elevation(terrain, [background, tiny, large], config)
    tiny_mask = _disc_mask(8, 12, 1, _FRAME)
    large_mask = _disc_mask(48, 12, 2, _FRAME)

    assert np.all(result.tiers[tiny_mask] == 0)
    assert np.all(result.tiers[large_mask] > 0)
    assert np.all(result.tiers[large_mask] <= PROMINENCE_TIER_MAX)

    # The same small hill survives the authored default minimum of four.
    default = generate_elevation(terrain, [background, tiny, large])
    assert default.tiers[12, 8] == 3


def test_region_amplitudes_mirror_the_classifier():
    terrain = synthetic_terrain()
    config = DEFAULT_ELEVATION_CONFIG
    amplitudes = region_amplitudes(terrain, config)
    expected = {
        "north_deep_forest": config.amplitude_forest,
        "northwest_highland_forest": config.amplitude_forest,
        "central_mountains": config.amplitude_mountains,
        "western_hills_valleys": config.amplitude_hills,
        "eastern_plains": config.amplitude_open,
        "southeast_coast": config.amplitude_coast,
        "southwest_coast": config.amplitude_coast,
    }
    assert set(expected) == set(REGION_KEYS)
    assert amplitudes.shape == (_FRAME, _FRAME)
    for y in range(_FRAME):
        for x in range(_FRAME):
            region = region_for_coordinates(terrain, x, y)
            assert amplitudes[y, x] == expected[region]


def test_directional_residual_noise_autocorrelation_stays_below_limit():
    config = replace(
        DEFAULT_ELEVATION_CONFIG,
        base_wavelength=4.0,
        octaves=4,
        persistence=0.5,
        lacunarity=2.0,
        warp_strength=1.0,
        warp_wavelength=16.0,
    )
    field = fractal_noise(64, 64, config)
    first_lag = int(2 * config.base_wavelength)

    for lag in range(first_lag, 33):
        for delta_x, delta_y in (
            (lag, 0),
            (0, lag),
            (lag, lag),
            (lag, -lag),
        ):
            correlation = _lag_correlation(field, delta_x, delta_y)
            assert abs(correlation) <= 0.30, (lag, delta_x, delta_y, correlation)


def test_domain_warping_changes_the_noise_field():
    plain = replace(DEFAULT_ELEVATION_CONFIG, warp_strength=0.0)
    warped = replace(DEFAULT_ELEVATION_CONFIG, warp_strength=2.0)

    warped_field = fractal_noise(32, 32, warped)
    assert not np.array_equal(fractal_noise(32, 32, plain), warped_field)
    assert np.array_equal(warped_field, fractal_noise(32, 32, warped))


def test_config_is_immutable_versioned_and_validated():
    config = DEFAULT_ELEVATION_CONFIG

    assert config.version == ELEVATION_CONFIG_VERSION
    with pytest.raises(FrozenInstanceError):
        config.seed = 7  # type: ignore[misc]

    for overrides in (
        {"amplitude_hills": 0.1},
        {"prominence_thresholds": (2.0, 1.0, 3.0)},
        {"ring_inner_radius": 9},
        {"ring_outer_radius": 1},
        {"octaves": 0},
        {"base_wavelength": 0.0},
        {"min_cluster_area": 0},
        {"version": 0},
    ):
        with pytest.raises(ValueError):
            replace(config, **overrides)
