# Design

## Context

See proposal.md (Why). The repository already provides these inputs, and this change reuses them.

- `elosern_map_core.discover_source_documents(root)` and `elosern_map_core.load_authoring_world(sources)` return an `AuthoringWorld` with these fields: `continent`, `locations` (`.locations[id]` is a `LocationDeclaration` with `.kind` and `.cell`), `districts`, `settlements` (map id → `SettlementDocument`) and `interiors`. When the sources do not load, the call raises `elosern_map_core.diagnostics.AuthoringError`.
- `elosern_map_core.authoring.terrain_definition(world.continent)` returns a `TerrainDefinition` with:
  - `.frame_cells`;
  - `.waterway_routes`: name → vertex tuple, from source to mouth;
  - `.waterway_fords`: name → ford cell tuple.
- The `elosern_map_core.terrain` module provides `is_land_cell(T, c)`, `is_inland_water_cell(T, c)`, `is_walkable_cell(T, c)` and `rasterize_routes({name: route})`.
- `elosern_map_core.authoring.gate_approach_cell(geometry, return_direction)` returns a gate's approach cell, or `None`. `SettlementDocument.wilderness_geometry(location_cell)` returns `.footprint_cells` (empty for a point shape), `.is_point_shape` and `.anchor_cell`.
- `content/maps/wilderness_elevation.json` holds `tiles: [{x, y, data}]`, which are 64×64 tiles. `elosern_map_core.elevation_codec.decode_tile(data, tx, ty, frame_cells)` returns 4096 bytes. The band of cell `(x, y)` is `decoded[(y % 64) * 64 + (x % 64)] >> 4`, taken from the tile `(x // 64, y // 64)`.
- `world.lore.anchors.ANCHOR_LORE[id]` has `.nation_key` and `.population`. Importing it in the game environment (`uv run --locked python`) needs no Django setup. This was verified; the map-core environment cannot import it.
- Top-level tests use `unittest` and may load `tools/map-editor/tests/synthetic_workspace.py` by file path, as `tests/test_map_image_capture.py` does. Its `write_workspace(root)` writes a 40×40 continent with these parts:
  - mainland is the whole frame;
  - river `synthetic_river`, routed from (20,20) to (0,20), with a ford at (10,20);
  - a ridge near x=25…28;
  - location `synthetic_place` at (5,5), with kind `capital`, and its point-shape settlement `synthetic_town`.

  `tree_digest(root)` hashes a tree.

## Goals / Non-Goals

**Goals:** the pure functions take explicit inputs, so they can be tested synthetically. A thin workspace adapter connects them to the real repository.

**Non-Goals:**
- graph generation (`settlement-graph-generator`);
- writing any file;
- a CI gate over shipped data;
- changes to `check_map_sources.py`, whose exit-code contract other tests pin.

## Decisions

### D1. Package layout and where it lives

We put the code in `tools/settlement_synthesis/`, a game-side tool package like `tools/map_district_partition.py`. It needs `ANCHOR_LORE`, which only the game environment can import, so the alternatives fail:

- skill scripts run in the map-core environment, which cannot import that lore;
- `packages/map-core` must stay free of game lore.

Files and responsibilities:

| File | Owns |
| --- | --- |
| `__init__.py` | docstring only |
| `geometry.py` | `Cell`, `OCTANTS`, `OPPOSITE`, `OCTANT_VECTORS`, `bearing`, `octant_distance`, `world_position`, `cell_of`, `point_to_cell_distance` |
| `terrain_view.py` | `GridTerrain` |
| `site.py` | `SettlementRef`, `WaterContact`, `PointFeature`, `SiteContext`, `analyse_site` |
| `budget.py` | `NATIONAL_KINDS`, `Tier`, `BudgetConfig`, `DEFAULT_BUDGET`, `SizeBudget`, `BudgetError`, `size_budget` |
| `fit_lint.py` | `WATER_EDGE_WORDS`, `CROSSING_WORDS`, `words`, `FitFinding`, `LintConfig`, `lint_settlement` |
| `workspace.py` | `WorkspaceError`, `WorkspaceView`, `load_workspace`, `load_lore` |
| `__main__.py` | argparse CLI `site`, `budget`, `lint` |

Contracts. Copy them verbatim:

```python
# geometry.py
Cell = tuple[int, int]
OCTANTS = ("e", "ne", "n", "nw", "w", "sw", "s", "se")          # index i = angle i*45° from east, counter-clockwise
OPPOSITE = {"n": "s", "ne": "sw", "e": "w", "se": "nw", "s": "n", "sw": "ne", "w": "e", "nw": "se"}
OCTANT_VECTORS = {"e": (1, 0), "ne": (1, 1), "n": (0, 1), "nw": (-1, 1),
                  "w": (-1, 0), "sw": (-1, -1), "s": (0, -1), "se": (1, -1)}

def bearing(dx: float, dy: float) -> str | None:
    """8-way bearing; dx east, dy north; None for the zero vector."""
    if dx == 0 and dy == 0:
        return None
    index = int(math.floor(math.atan2(dy, dx) / (math.pi / 4) + 0.5)) % 8
    return OCTANTS[index]

def octant_distance(a: str, b: str) -> int:          # 0..4
    i, j = OCTANTS.index(a), OCTANTS.index(b)
    return min(abs(i - j), 8 - abs(i - j))

def world_position(location_cell: Cell, anchor_m: tuple[int, int], local_m: tuple[int, int]) -> tuple[int, int]:
    return (1000 * location_cell[0] + 500 + local_m[0] - anchor_m[0],
            1000 * location_cell[1] + 500 + local_m[1] - anchor_m[1])

def cell_of(world_m: tuple[float, float]) -> Cell:
    return (int(math.floor(world_m[0] / 1000)), int(math.floor(world_m[1] / 1000)))

def point_to_cell_distance(world_m: tuple[float, float], cell: Cell) -> float:
    """Metres from a point to the nearest point of a 1 km cell square (0 inside)."""
    x0, y0 = 1000 * cell[0], 1000 * cell[1]
    dx = max(x0 - world_m[0], 0.0, world_m[0] - (x0 + 1000))
    dy = max(y0 - world_m[1], 0.0, world_m[1] - (y0 + 1000))
    return math.hypot(dx, dy)
```

```python
# terrain_view.py
@dataclass(frozen=True)
class GridTerrain:
    window: tuple[int, int, int, int]                    # min_x, min_y, max_x, max_y (inclusive)
    land: frozenset[Cell]                                # mainland cells inside the window
    inland_water: frozenset[Cell]                        # waterway raster minus fords
    impassable: frozenset[Cell]                          # land, not water, not walkable (ridge walls)
    waterway_routes: Mapping[str, tuple[Cell, ...]]      # source -> mouth vertices (whole route)
    waterway_cells: Mapping[str, frozenset[Cell]]        # raster cells per waterway inside the window, fords excluded
    waterway_fords: Mapping[str, tuple[Cell, ...]]
    bands: Mapping[Cell, int]                            # elevation band 0..15; missing = 0
    harbours: Mapping[str, Cell]

    def contains(self, cell: Cell) -> bool       # inside window
    def is_sea(self, cell: Cell) -> bool         # contains and not in land
    def is_water(self, cell: Cell) -> bool       # is_sea or in inland_water   (fords are never water)
    def walkable(self, cell: Cell) -> bool       # contains, in land, not inland_water, not impassable
    def band(self, cell: Cell) -> int            # bands.get(cell, 0)
```

```python
# site.py
@dataclass(frozen=True)
class SettlementRef:
    location_id: str
    kind: str
    nation: str | None
    population: int | None
    cell: Cell

@dataclass(frozen=True)
class WaterContact:
    kind: str                 # "river" | "sea"
    name: str | None          # waterway id; None for sea
    distance_cells: float     # Euclidean, location cell -> nearest_cell
    bearing: str              # bearing of the centroid of that body's cells within the radius
    nearest_cell: Cell        # min by (distance, y, x)
    downstream: str | None    # river: bearing(end - start) of the route segment nearest to nearest_cell

@dataclass(frozen=True)
class PointFeature:
    feature_id: str
    cell: Cell
    distance_cells: float
    bearing: str | None

@dataclass(frozen=True)
class SiteContext:
    location_id: str
    kind: str
    nation: str | None
    population: int | None
    cell: Cell
    rivers: tuple[WaterContact, ...]       # sorted by (distance_cells, name)
    sea: WaterContact | None
    fords: tuple[PointFeature, ...]        # feature_id = waterway id; sorted (distance, id, cell)
    harbours: tuple[PointFeature, ...]     # feature_id = harbour id; sorted (distance, id)
    uphill: str | None
    relief: int
    neighbours: tuple[PointFeature, ...]   # feature_id = location id; sorted (distance, id)
    capital_bearing: str | None

def analyse_site(location: SettlementRef, terrain: GridTerrain, roster: Sequence[SettlementRef], *,
                 radius: int = 8, relief_radius: int = 3, harbour_radius: int = 15,
                 neighbour_count: int = 4) -> SiteContext
```

The `analyse_site` rules:

- "Within the radius" means Chebyshev distance `max(|dx|, |dy|) ≤ radius` from `location.cell`. Distances are Euclidean, `math.hypot` over cell indices.
- Rivers: for each waterway name in sorted order, gather the cells of `waterway_cells[name]` within the radius. An empty set produces no contact.
- `downstream`: for each segment `(route[i], route[i+1])`, compute the point-to-segment distance from `nearest_cell`. Take the smallest, with ties going to the lowest `i`. The result is `bearing(end - start)` of that segment.
- Sea: gather the cells in the window, within the radius, where `is_sea` holds. Use the same nearest-cell and centroid rules, with `name=None` and `downstream=None`.
- Fords: every ford of every waterway within the radius.
- Harbours: every harbour within `harbour_radius`.
- Relief and uphill:
  - Let `cells` be the walkable cells within `relief_radius`, plus the location cell.
  - `relief = max(band) - min(band)` over `cells`.
  - `gradient = Σ (band(c) - band(location)) * (c - location)`.
  - `uphill = bearing(gradient)` when `relief ≥ 1`, otherwise `None`.
- Neighbours: the roster rows, excluding self, whose `kind` is in `NATIONAL_KINDS`. Take the first `neighbour_count` by `(distance, id)`.
- `capital_bearing`: `None` when the location is itself a capital or has no nation. Otherwise it is the bearing to the first roster row (by id) with `kind == "capital"` and the same nation, or `None` when there is no such row.

```python
# budget.py
NATIONAL_KINDS = ("capital", "city", "town", "port")

@dataclass(frozen=True)
class Tier:
    min_population: int
    nodes: int
    gates: int
    loop_ratio: float

@dataclass(frozen=True)
class BudgetConfig:
    reference_population: int
    reference_density_per_ha: float
    area_exponent: float
    min_footprint_cells: int
    tiers: tuple[Tier, ...]
    capital_tier: Tier
    def __post_init__(self): # ValueError if min_footprint_cells < 2, no tiers, or any non-positive constant

DEFAULT_BUDGET = BudgetConfig(
    reference_population=10_000,
    reference_density_per_ha=150.0,
    area_exponent=0.714,
    min_footprint_cells=2,
    tiers=(Tier(100_000, 18, 3, 0.30), Tier(50_000, 12, 2, 0.25), Tier(25_000, 10, 2, 0.20),
           Tier(10_000, 8, 2, 0.15), Tier(0, 6, 2, 0.15)),
    capital_tier=Tier(0, 28, 4, 0.35),
)

@dataclass(frozen=True)
class SizeBudget:
    location_id: str
    population: int
    built_area_km2: float
    footprint_cells: int
    envelope_radius_m: int
    node_count: int
    gate_count: int
    loop_ratio: float

class BudgetError(ValueError): ...

def size_budget(location: SettlementRef, config: BudgetConfig = DEFAULT_BUDGET) -> SizeBudget
```

The `size_budget` rules, in order:

1. A `kind` outside `NATIONAL_KINDS`, or a population of `None` or less than 1, raises `BudgetError(f"{location.location_id}: ...")`.
2. `ref_area_km2 = reference_population / reference_density_per_ha / 100`. A km² is 100 ha.
3. `area = ref_area_km2 * (population / reference_population) ** area_exponent`.
4. `footprint_cells = max(min_footprint_cells, math.ceil(area - 1e-9))`.
5. `envelope_radius_m = round(1000 * math.sqrt(area / math.pi))`.
6. The tier is `capital_tier` when `kind == "capital"`. Otherwise it is the tier with the greatest `min_population ≤ population`. If no tier qualifies, raise `BudgetError`.

### D2. The size reference is an assumption, recorded once

**Exponent.** Cesaretti et al. (2016, *PLOS ONE*) give an exponent of about 0.714 over 173 medieval European cities. That paper is the research basis (tmp/Elosern_Settlement_Research_2026.md item 12).

**Density anchor.** The user's brief and the late-medieval walled-town literature describe densities of roughly 100–250 inhabitants per hectare. 150/ha at 10,000 people is the mid-range anchor, which gives about 0.67 km². The user accepted this anchor on 2026-11-02; it is a tunable default in the size budget, not a verified constant. With exponent 0.714, density rises as population^0.286. Illustrative default output:

| population | area km² | cells | envelope radius m | inh/ha |
| ---: | ---: | ---: | ---: | ---: |
| 6,000 | 0.46 | 2 | 384 | 130 |
| 25,000 | 1.28 | 2 | 639 | 195 |
| 55,000 | 2.25 | 3 | 847 | 244 |
| 180,000 | 5.25 | 6 | 1,293 | 343 |
| 400,000 | 9.28 | 10 | 1,719 | 431 |
| 600,000 | 12.40 | 13 | 1,987 | 484 |
| 800,000 | 15.23 | 16 | 2,202 | 525 |

The capitals' 430–525/ha is above historical walled-town norms. That is the explained fantasy constraint: magical-era multi-storey building and regional supply, per the continental-geography "Large fantasy capitals" scenario. We do not recompute the capitals' populations.

**Node tiers.** The tiers set a gameplay budget, so they grow log-like and not linearly with population. Gate counts are 4 for a capital, 3 at ≥100k and 2 otherwise. Loop ratios are 0.35, 0.30, 0.25, 0.20 and 0.15.

**Human review.** Whether these feel right in play is human-reviewed and not tested. `docs/development/settlement-synthesis.md` § Human review lists the checks.

### D3. The two scales are explicit

The footprint is wilderness occupancy, in whole 1 km cells: a cell becomes "town" instead of wilderness. The envelope radius is the metre extent of the street graph, whose polyline lengths are walking time at 1.25 m/s. Both derive from one built-up area. Rounding the footprint up to whole cells absorbs walls, suburbs and gardens. The street extent stays at the built-up size, so a 6,000-person town is about 770 m across, a 10-minute walk, while a 600k capital is about 4 km across. The lint enforces the link between the scales in one direction: a node must stand inside a footprint cell.

### D4. Lint rules (`fit_lint.py`)

```python
WATER_EDGE_WORDS = frozenset({"quay", "wharf", "dock", "docks", "pier", "landing", "riverbank", "waterfront"})
CROSSING_WORDS = frozenset({"bridge", "ford", "ferry"})

def words(node_id: str) -> frozenset[str]:
    return frozenset(node_id.split("_"))

@dataclass(frozen=True)
class FitFinding:
    code: str        # see table
    severity: str    # "error" | "warning"
    map_id: str
    object_id: str   # node id, "source>destination" for a road, "gate:<return_direction>" for a gate
    message: str

@dataclass(frozen=True)
class LintConfig:
    water_edge_max_m: int = 600
    sample_step_m: int = 50

def lint_settlement(document, location_cell: Cell, terrain: GridTerrain,
                    config: LintConfig = LintConfig()) -> tuple[FitFinding, ...]
```

Node world position is `world_position(location_cell, document.local_anchor_m, node.coordinate)`. Findings are sorted by `(severity == "warning", code, object_id)`, so errors come first. Codes:

| Code | Severity | Rule |
| --- | --- | --- |
| `fit_missing_anchor` | error | `document.local_anchor_m is None`. Report only this finding and return. |
| `fit_node_in_water` | error | `terrain.is_water(cell_of(world))`, for every map |
| `fit_water_role_dry` | error | `words(id) & WATER_EDGE_WORDS`, and `min(point_to_cell_distance(world, c) for water c in window) > water_edge_max_m`. No water in the window also triggers it. |
| `fit_unbridged_crossing` | error | The road polyline (source, bends, destination, in world metres) is sampled every `≤ sample_step_m`: `n = max(1, ceil(len/step))` points per segment, endpoints included. Some sample has `is_water(cell_of(p))`, and neither endpoint id has a `CROSSING_WORDS` word. |
| `fit_node_outside_footprint` | error | Multi-cell only: `cell_of(world) not in geometry.footprint_cells` |
| `fit_gate_approach_blocked` | error | Multi-cell only: `gate_approach_cell(geometry, rd)` is `None` or not `terrain.walkable` |
| `fit_gate_side` | warning | Multi-cell only. Let `v = gate_node.coordinate - anchor` and `o = OCTANT_VECTORS[OPPOSITE[rd]]`. The finding fires when `v != (0,0)` and `v·o < 0`. |
| `fit_direction_drift` | warning | Take the first segment, from source to the first bend or to the destination, in local metres. The finding fires when it has non-zero length and `octant_distance(road.direction, bearing(segment)) > 1`. |

### D5. Workspace adapter and CLI

```python
# workspace.py
class WorkspaceError(Exception): ...          # sources do not load / unknown id; carries a message

def load_lore(path: Path | None) -> Mapping[str, tuple[str | None, int | None]]:
    """None -> world.lore.anchors.ANCHOR_LORE as {id: (nation_key, population)};
    a path -> JSON {id: {"nation": str|null, "population": int|null}}."""

@dataclass(frozen=True)
class WorkspaceView:
    root: Path
    world: Any                                   # AuthoringWorld
    roster: tuple[SettlementRef, ...]           # every location, sorted by id; lore-missing -> (None, None)
    def location(self, location_id: str) -> SettlementRef        # WorkspaceError if unknown
    def terrain_window(self, centre: Cell, radius: int) -> GridTerrain

def load_workspace(root: Path, lore: Path | None = None) -> WorkspaceView   # AuthoringError -> WorkspaceError
```

`terrain_window` loops over every cell of the clamped square `[centre-radius, centre+radius]` inside `[0, frame_cells)`.

- `land` holds the cells where `is_land_cell` is true.
- `inland_water` holds the cells where `is_inland_water_cell` is true.
- `impassable` holds land cells that are not inland water and not `is_walkable_cell`.
- Per waterway, `waterway_cells` is `rasterize_routes({name: route})` minus that waterway's fords, intersected with the window. Compute the full raster once per `WorkspaceView` and cache it in a private dict.
- `bands` come from `content/maps/wilderness_elevation.json`. A missing file gives `{}`; decode each tile once and cache it.
- `harbours` come from `world.continent.harbor_sites` (`.cell`).

The lint window for one map. It is sized from every cell the lint reads, so the
whole of each road polyline stays inside the window (the window is a convex
square, so any sampled point of a segment whose endpoints are inside is inside
too):

```
radius = max(8, 3 + max Chebyshev distance from the location cell to any node cell, road bend cell, footprint cell or gate approach cell)
```

CLI (`python -m tools.settlement_synthesis`):

```
site LOCATION_ID [--root DIR] [--lore FILE] [--radius N]      -> JSON SiteContext on stdout, exit 0
budget LOCATION_ID [--root DIR] [--lore FILE]                  -> JSON SizeBudget on stdout, exit 0; BudgetError -> stderr, exit 1
lint [MAP_ID ...] [--root DIR]                                 -> one line per finding, then a summary; exit 0/1/2
```

- JSON output uses `json.dumps(dataclasses.asdict(obj), ensure_ascii=False, indent=2, sort_keys=True)`, with tuples emitted as lists.
- A lint finding line is `f"{severity.upper()} {code} {map_id} {object_id}: {message}"`. The last line is `fit: {errors} errors, {warnings} warnings`.
- `WorkspaceError` prints to stderr and exits 2. An unknown map id given to `lint` also exits 2.
- `--root` defaults to the current directory. Nothing is ever written.

### D6. Tests (`tests/test_settlement_terrain_fit.py`)

- The tests use `unittest.TestCase` only.
- The pure-function tests build `GridTerrain` values in memory.
- The CLI tests run `[sys.executable, "-m", "tools.settlement_synthesis", ...]` with `cwd=REPO_ROOT`, `--root <tmpdir>` and `--lore <tmpfile>`, on `synthetic_workspace.write_workspace(tmp)`. They compare `synthetic_workspace.tree_digest(tmp)` before and after each run.
- No shipped location, map or node id may appear. `tools.test_data_lint check` must stay green.

Requirement → test mapping. The decorators are added at archive, because the IDs exist only after sync:

| Requirement ID | Test class |
| --- | --- |
| `settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain` | `SiteContextTests` |
| `settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor` | `SizeBudgetTests` |
| `settlement-terrain-fit::terrain-fit-lint-flags-dry-water-edge-roles-and-unbridged-crossings` | `WaterAndCrossingLintTests` |
| `settlement-terrain-fit::terrain-fit-lint-checks-footprint-water-gate-side-and-gate-approach` | `FootprintAndGateLintTests` |
| `settlement-terrain-fit::road-direction-drift-is-a-warning` | `DirectionDriftLintTests` |
| `settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status` | `CommandTests` |

## Risks / Trade-offs

- [The lint fails on master for `capital_altoria` (dry `quay` and `riverbank_road`)] → Expected and documented in the skill. `altoria-capital-river-rework` fixes it. No CI gate depends on the lint.
- [Word-based roles can be fooled by an id like `old_dock_lane` that is not really a quay] → This is accepted: ids are permanent and English, and the whole-word rule keeps false positives rare. A true false positive is renamed only with the user's consent, because ids are permanent.
- [The 1 km raster cannot represent a stream inside a cell] → The lint treats only raster water as water. That is why the water-edge limit is 600 m and not 0.
- [Synthetic workspace drift] → The tests use only the documented `write_workspace` and `tree_digest` and edit documents through `ruamel` as that module does.

## Migration Plan

None. This change adds tooling only.
