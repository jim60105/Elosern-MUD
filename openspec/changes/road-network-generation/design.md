# Design

## Context

See `proposal.md` for motivation. `docs/superpowers/specs/2026-11-07-official-roads-design.md` is the approved design; this document fixes what that design leaves open and records where the code required a different placement.

Facts verified against the code and a read-only prototype on the shipped map (scratch only, nothing committed):

- `partition_input()` already rasterizes `walkable` and `region`; `walkable` excludes footprints.
- Removing the forbidden region leaves exactly two 4-connected walkable components. All node approach cells fall in one of them.
- `scipy.sparse.csgraph.dijkstra` with `min_only=True` covers the whole cost field fast enough for one run per node plus one per road. Peak memory was about 2 GB.
- With the initial detour limit and no slope or noise, topology produced 59 nodes, 122 terrain-neighbour pairs, 71 relative neighbourhood pairs and 7 detour additions, with no isolated node and no shared approach cell. These are observations for orientation, not requirements.

## Goals / Non-Goals

**Goals:** the units in the approved design's table except the runtime reader, byte-reproducible output, and a self-check that does not trust the router.

**Non-Goals:** `world/maps/runtime.py`, `world/maps/road_network.py`, `wilderness_terrain` and `area_map.py` belong to `road-network-runtime`. Do not touch them here. Do not edit any file under `tools/map-editor/`. Do not add map editor regeneration. Do not tune parameters to satisfy a test.

## Decisions

### D1. New optional singleton document kind

`road_network` is a real source kind, so it joins the world fingerprint and editor file following by the existing rules.

- `sources.py`: add `"content/maps/road_network.yaml": ("road_network", "road_network")` to `FIXED_SOURCES`; update the module docstring.
- `authoring.py`: add `"road_network"` to `WORLD_SOURCE_KINDS`. Do **not** add it to the required loop `for kind in ("continent", "locations", "districts")`. Add `road_network: RoadNetworkDocument | None` to `AuthoringWorld` after `interiors`, and pass the parsed entry's `.document`, or `None` when no entry exists, into both constructors in `load_authoring_world`.
- After `_structural_diagnostics(...)` add a check that every `forbidden_regions` entry is in `continent.regions`, code `unknown_road_region`, category `STRUCTURE`, field path `forbidden_regions`.

Alternative rejected: a required document. It would edit every synthetic world in `authoring_fixtures.py`, `synthetic_workspace.py` and the top-level contract tests for a document those worlds never read. `docs/development/map-authoring-documents.md` says missing singletons fail the load, so that sentence is amended to name this exception.

Schema entry in `_DOCUMENT_KINDS`, `kind: road_network`, fixed id `road_network`:

| Field | Spec |
| --- | --- |
| `version` | `_int(constant=SCHEMA_VERSION)` |
| `kind` | `_enum(("road_network",))` |
| `id` | `_str(pattern=IDENTIFIER_PATTERN, constant="road_network")` |
| `node_kinds` | `_list(_enum(LOCATION_KINDS), min_items=1)` |
| `forbidden_regions` | `_list(_str(pattern=IDENTIFIER_PATTERN))` |
| `slope_factor_per_band` | `_number(min_value=0)` |
| `noise_amplitude` | `_number(min_value=0, max_value=0.9)` |
| `noise_wavelength_cells` | `_number(min_value=2)` |
| `noise_seed` | `_int(min_value=0)` |
| `detour_limit` | `_number(min_value=1)` |
| `reuse_factor` | `_number(min_value=0.01, max_value=1)` |

`documents.py`: `RoadNetworkDocument(AuthoringDocument)` follows `LocationsDocument`, exposing each field by the same name with lists as tuples and numbers as `float`. Register it in `DOCUMENT_CLASSES`.

Shipped `content/maps/road_network.yaml` initial values are starting points, tuned from the preview:

```yaml
version: 1
kind: road_network
id: road_network
node_kinds: [capital, city, port, town]
forbidden_regions: [north_deep_forest]
slope_factor_per_band: 0.15
noise_amplitude: 0.15
noise_wavelength_cells: 48
noise_seed: 20261107
detour_limit: 1.8
reuse_factor: 0.4
```

### D2. Pure algorithm contract

`packages/map-core/elosern_map_core/roads.py` imports NumPy and SciPy at module level, like `partition.py`, and is never imported by `elosern_map_core/__init__.py`.

```python
Cell = tuple[int, int]

class RoadGenerationError(ValueError):
    """problems: tuple[str, ...]; str(error) lists every problem."""

@dataclass(frozen=True)
class RoadNode:
    key: str                      # location key
    approaches: tuple[Cell, ...]  # sorted, unique

@dataclass(frozen=True, eq=False)
class RoadInput:
    size: int
    walkable: np.ndarray          # bool [y, x]; footprints already False
    region: np.ndarray            # uint8 [y, x]; index + 1 into region_names, 0 = sea
    region_names: tuple[str, ...]
    bands: np.ndarray             # uint8 [y, x], 0..15
    region_speeds: Mapping[str, int]  # metres per hour
    nodes: tuple[RoadNode, ...]   # sorted by key
    blocked: frozenset[Cell]
    forbidden_regions: tuple[str, ...]
    slope_factor_per_band: float
    noise_amplitude: float
    noise_wavelength_cells: float
    noise_seed: int
    detour_limit: float
    reuse_factor: float
    source_signature: str

@dataclass(frozen=True)
class Road:
    first: str                    # first < second
    second: str
    cells: tuple[Cell, ...]       # first's approach ... second's approach

def road_input(world: AuthoringWorld, bands: np.ndarray,
               region_speeds: Mapping[str, int],
               elevation_fingerprint: str) -> RoadInput: ...
def compute_roads(inp: RoadInput) -> tuple[Road, ...]: ...      # sorted by (first, second)
def verify_roads(inp: RoadInput, roads: Sequence[Road]) -> list[str]: ...
def encode_roads(inp: RoadInput, roads: Sequence[Road]) -> str: ...
def generate_road_network(inp: RoadInput) -> str: ...
```

`road_input` raises `RoadGenerationError` naming `content/maps/road_network.yaml` when `world.road_network is None`. It rasterizes through `partition_input(PartitionInputSnapshot(terrain=terrain_definition(world.continent), nation_names=NATION_KEYS, region_names=tuple(sorted(world.continent.regions)), footprints=<every settlement entry's footprint>, districts=(), source_signature=""))`. It iterates `world.settlements` as `partition.world_snapshot` does, using `settlement.wilderness_geometry(location_cells[settlement.location_ref])` and `gate_approach_cell(geometry, gate.return_direction)`. A settlement with at least one approach and a configured location kind is a node, keyed by `location_ref`. The anchor cell of a point-shape entry (`geometry.is_point_shape`) that is not a node goes into `blocked`: the planner diverts its gate direction into the grid, so a road through it would contain a step the runtime refuses.

`generate_road_network(inp)` is `_check_input`, then `compute_roads`, then `verify_roads`, then `encode_roads`. Any problem raises `RoadGenerationError`.

### D3. Cost field

`open = walkable & ~forbidden & ~blocked`. Build one CSR graph over `open` cells with the eight directions; a diagonal needs both orthogonal cells open, as in `world/rules/travel_plan.py::_route`. The legal connectivity therefore equals 4-connectivity, and `scipy.ndimage.label(open)` gives the networks' components.

Step weight between cells `a` and `b`, as an integer in milliseconds, so that platform differences in a float's last bit cannot change the output:

```text
seconds_per_cell(c) = 3_600 * 1000 / region_speeds[region(c)]     # one km cell
base = max(1, rint(1000 * step * max(seconds_per_cell(a), seconds_per_cell(b))
                   * (1 + slope_factor_per_band * abs(bands[a] - bands[b]))
                   * (1 + noise_amplitude * (noise[a] + noise[b]) / 2)))
```

`step` is `1` or `sqrt(2)`. `noise` is `elevation.fractal_noise(size, size, replace(DEFAULT_ELEVATION_CONFIG, seed=noise_seed, base_wavelength=w, warp_wavelength=2 * w))` with `w = noise_wavelength_cells`, in `[-1, 1]`. The averaged endpoints and the absolute band difference keep the graph symmetric, so `d(A, B) == d(B, A)`. A region with an open cell and no speed raises `RoadGenerationError` naming the region.

### D4. Topology and routing

- `d[i][j]` is `dijkstra(graph, indices=node_i_cells, min_only=True)` read at node `j`'s approach cells, minimum taken. It is infinite across components.
- Terrain neighbours: `dijkstra(graph, indices=all_approaches, min_only=True, return_predecessors=True)` returns `sources`; map each source to its node, then take unique owner pairs across graph edges.
- Relative neighbourhood: keep `i < j` with finite `d` unless some `k` has `d[i][k] < d[i][j]` and `d[k][j] < d[i][j]`.
- Detour repair: over terrain neighbours, compute `ratio = network_cost / max(d, 1)` where `network_cost` is the shortest path over kept pairs weighted by `max(d, 1)`. While the greatest ratio exceeds `detour_limit`, add the pair that sorts first by `(-ratio, first, second)` and recompute.
- Routing: sort kept pairs by `(d, first, second)`. For each, run `dijkstra(graph, indices=first_cells, min_only=True, return_predecessors=True)`, take the second node's approach cell with the lowest `(cost, y, x)`, and backtrack. After each road, set every edge with both ends on a road cell to `max(1, rint(base * reuse_factor))`. The edge test matches the runtime rule that a step is on the road only when both ends are road cells.

### D5. Independent self-check

`verify_roads` recomputes `open` and its components and does not read the router's state. It returns one problem string for each of:

- `node <key>: has no road`
- `road <first>--<second>: cell <cell> is off the cost field`
- `road <first>--<second>: illegal step <cell> -> <cell>`
- `road <first>--<second>: does not end at gates of its settlements`
- `network <component>: nodes <keys> are not connected`
- `road <first>--<second>: joins separate networks`

`_check_input` reports `node <key>: gate approach <cell> is off the cost field` before computing. A candidate from `compute_roads` cannot trigger most of these, which is why tests feed `verify_roads` hand-built roads.

### D6. Codec contract

`packages/map-core/elosern_map_core/roads_codec.py` imports the standard library and `.sources` only.

```python
FORMAT_VERSION = 1
ROAD_ALGORITHM_VERSION = 1
ROAD_SOURCE_KINDS = frozenset({"continent", "locations", "settlement", "road_network"})

class RoadDocumentError(ValueError): ...

@dataclass(frozen=True, slots=True)
class RoadFreshness:
    algorithm_version: int
    input_signature: str
    current: bool

@dataclass(frozen=True, slots=True)
class RoadMetadata:
    format_version: int
    algorithm_version: int
    source_signature: str
    fingerprint: str

@dataclass(frozen=True, eq=False)
class RoadNetwork:
    fingerprint: str
    roads: tuple[tuple[str, str, tuple[tuple[int, int], ...]], ...]
    cells: frozenset[tuple[int, int]]

def road_source_signature(fingerprints: Mapping[str, str], *,
                          elevation_fingerprint: str,
                          region_speeds: Mapping[str, int]) -> str: ...
def road_freshness(metadata: RoadMetadata, source_signature: str | None,
                   algorithm_version: int = ROAD_ALGORITHM_VERSION) -> RoadFreshness: ...
def read_road_metadata(source: Mapping | str) -> RoadMetadata: ...
def decode_road_network(source: Mapping | str) -> RoadNetwork: ...
```

`road_source_signature` follows `partition_source_signature_from_fingerprints`: it hashes the sorted `(path, fingerprint)` rows of `ROAD_SOURCE_KINDS`, then the elevation fingerprint, then sorted `(region, speed)` rows. A falsy signature is never current, matching `partition_freshness`.

The approved design's input list names terrain time but not where it comes from. Speeds stay in `world/rules/rulebook/movement.yaml`, the single authority, and they join the signature, so a speed change reads as stale. Elevation joins for the same reason.

Artifact layout, with one road per line:

```json
{
  "algorithm_version": 1,
  "fingerprint": "<sha256 over the canonical nodes and roads>",
  "frame_cells": 2700,
  "nodes": ["<key>"],
  "roads": [
    {"cells": [0, 0, 1, 1], "first": "<key>", "second": "<key>"}
  ],
  "source_signature": "<sha256>",
  "version": 1
}
```

`cells` is flat `[x0, y0, x1, y1, ...]`. Each road object is `json.dumps(road, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`. `decode_road_network` rejects a wrong `version`, a non-string `first` or `second`, `first >= second`, an empty or odd `cells`, a non-integer or boolean coordinate, a coordinate outside `0..frame_cells - 1`, and a fingerprint that disagrees with the recomputed value.

### D7. Game adapter

`tools/road_network.py` mirrors `tools/map_district_partition.py`: same `_bootstrap`, `DATA_PATH = REPOSITORY_ROOT / "world/maps/data/road_network.json"`, and arguments `--check`, `--output PATH`, plus `--preview PATH`.

```python
def band_raster(runtime) -> np.ndarray: ...   # decodes every tile with get_tile; band = byte >> 4
def build_input() -> RoadInput: ...
def artifact_text() -> str: ...
def write_preview(inp: RoadInput, roads, path: Path) -> None: ...
def main(argv=None) -> int: ...
```

`build_input` runs `composed = runtime.compose()`, `runtime.preview(composed)`, then `elevation.load_elevation(None, expected_frame_cells=world.continent.terrain.frame_cells)`. It raises `SystemExit` with a message when `elevation.freshness(metadata, continent_fingerprint)` is not current, because a road built on stale bands could never pass adoption. It then calls `road_input(world, band_raster(elevation_runtime), travel_cost.region_speeds_m_per_hour(), elevation_runtime.fingerprint)`.

Tile layout from `elevation_codec.encode_tile`: 64 by 64 bytes, row-major, `(band << 4) | tier`. Slice cells beyond the frame away.

`main` catches `RoadGenerationError`, prints every problem and returns 1. The output file is written only after generation succeeds. `write_preview` uses Pillow, which the root project already locks, and draws land, sea, unwalkable cells, fords, roads and node cells. Only an explicit `--preview` path writes an image, and that path is never in the repository.

`world/rules/travel_cost.py` gains, with an `__all__` entry:

```python
def region_speeds_m_per_hour() -> dict[str, int]:
    """Each wilderness region's authored speed, the road generator's terrain price."""
    return {region: terrain_speed_m_per_hour(terrain) for region, terrain in WILDERNESS_TERRAIN.items()}
```

### D8. CI gate

The approved design says "the existing CI gate", but CI runs no partition `--check`; the only artifact `--check` step is `Validate map reference context freshness`. Add a sibling step directly after it in `.github/workflows/quality-gate.yml`:

```yaml
      - name: Validate road network freshness
        run: uv run --locked python -m tools.road_network --check
```

Do not add it to `tools/contract_gate.py`: that gate is a seconds-long pre-handoff check, and this one regenerates the network.

### D9. Test placement

`covers_requirement` lives in `tools.spec_traceability`, which the pure map-core environment cannot import, so annotated mechanism tests go in top-level `tests/test_road_network_generation.py`, as `tests/test_map_partition_independence.py` does for the partition. They run in the root environment, which has NumPy and SciPy. The command test needs the game modules, so it lives in `world/maps/tests/test_road_network_command.py`.

All fixtures are small synthetic rasters built in the test file. No test names shipped regions, locations or counts, and no test measures time.

## Risks / Trade-offs

- [Initial parameters may look wrong on the map] → They are data in `content/maps/road_network.yaml`, tuned from the preview under human review. No test pins them.
- [A settlement or terrain edit makes the artifact stale, and the editor does not regenerate it] → CI fails here. `road-network-runtime` makes startup name the command. Editor regeneration is out of scope.
- [The generator peaks near 2 GB on the shipped map] → It runs offline and in CI only. Runtime never imports `roads.py`.
- [`fractal_noise` could change if elevation's config changes] → `ROAD_ALGORITHM_VERSION` guards intended changes, and `--check` catches accidental ones.

## Migration Plan

None. The network is recomputed whole. Regeneration order after a terrain change: partition, elevation, then `uv run --locked python -m tools.road_network`.
