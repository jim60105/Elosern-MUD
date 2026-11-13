# Design

## Context

Inputs that already exist:

- `content/maps/locations.yaml`: every location's kind, cell and display name (`LocationDeclaration` in `packages/map-core/elosern_map_core/documents.py`).
- `world/maps/data/road_network.json`: decoded by `elosern_map_core.roads_codec.decode_road_network` into `RoadNetwork.roads`, a tuple of `(first, second, cells)` where `cells` runs from the first settlement's end to the second's. The standard library is enough.
- `content/maps/continent.yaml`: each region's `nation_key`, empty for `central_mountains` and `north_deep_forest`. `elosern_map_core.terrain.region_for_coordinates(definition, x, y)` gives a cell's region.
- `content/maps/road_network.yaml`: `forbidden_regions`.
- `world.lore.anchors.ANCHOR_LORE`: nation and population. `tools.settlement_synthesis.workspace.load_lore(path)` already returns `{location_id: (nation, population)}` from the lore or from a JSON override, with no Django setup.

The road artifact has 78 roads over 15,415 cells today, so a linear pass over every road is cheap.

## Goals / Non-Goals

**Goals:**

- One pure function that returns every problem of a synthetic or shipped input.
- One command that CI runs.

**Non-Goals:**

- No placement, naming or candidate proposal. The placement script is not part of this change.
- No check of monster habitats. The existing publication check of ecology geometry owns that.
- No check of road artifact freshness. `tools.road_network --check` owns that.
- No retroactive check among capitals, cities, towns and ports.
- No change to the road generator. The check that a village stands on a road cell passes trivially until a village exists.
- No test over shipped locations. CI runs the command on them instead.

## Decisions

### D1. Module layout and contracts

`tools/settlement_spacing.py` holds the pure check and the command. The public contract:

```python
Cell = tuple[int, int]

@dataclass(frozen=True)
class SpacingConfig:
    hamlet_min_km: float = 15.0
    village_min_km: float = 40.0
    road_gap_max_km: float = 75.0
    village_population: tuple[int, int] = (300, 2000)
    hamlet_population: tuple[int, int] = (50, 300)

@dataclass(frozen=True)
class Place:
    location_id: str
    kind: str
    cell: Cell
    display_name_zh: str
    exemption: str | None
    nation: str | None        # from lore
    population: int | None    # from lore
    has_lore: bool

@dataclass(frozen=True)
class Area:
    area_id: str
    region: str
    bounds: tuple[int, int, int, int] | None   # x_min, y_min, x_max, y_max, inclusive

@dataclass(frozen=True)
class SpacingInput:
    places: tuple[Place, ...]
    roads: tuple[tuple[str, str, tuple[Cell, ...]], ...]
    region_of: Callable[[Cell], str]
    region_nation: Mapping[str, str | None]
    forbidden_regions: frozenset[str]
    areas: tuple[Area, ...]

@dataclass(frozen=True)
class Problem:
    code: str
    subject: str
    message: str

def check_spacing(inp: SpacingInput, config: SpacingConfig = SpacingConfig()) -> tuple[Problem, ...]: ...
def load_areas(path: Path) -> tuple[Area, ...]: ...
def build_input(root: Path, lore: Path | None, roads: Path, areas: Path) -> SpacingInput: ...
def main(argv: Sequence[str] | None = None) -> int: ...
```

`check_spacing` returns problems sorted by `(code, subject)`. The tests pass synthetic `SpacingInput` values, and synthetic `SpacingConfig` values where a threshold matters, so no test pins a shipped number.

Kind sets, as module constants:

```python
SMALL_KINDS = ("village", "hamlet")
NATIONAL_KINDS = ("capital", "city", "town", "port")
SETTLEMENT_KINDS = NATIONAL_KINDS + SMALL_KINDS       # elven_village and dungeon are excluded
```

Alternative considered: put the pure check in `packages/map-core`. Rejected: it needs no map-core internals beyond the decoded documents, and the lore join lives on the game side.

### D2. Minimum spacing

Distance between two places is `math.hypot(dx, dy)` over their cells, in kilometres (one cell is 1 km).

- For every hamlet `h` and every other place `p` with `p.kind in SETTLEMENT_KINDS`: a distance below `hamlet_min_km` is `hamlet_spacing`, subject `h.location_id`, message naming `p` and the distance to one decimal. A hamlet pair is reported once, under the smaller ID.
- For every village `v` and every other place `p` with `p.kind in NATIONAL_KINDS + ("village",)`: a distance below `village_min_km` is `village_spacing`, reported the same way. A village and a hamlet are governed by the hamlet rule only.
- A pair is skipped when either party is a village or hamlet whose `exemption` is not `None`. A mark on any other kind has no effect.

Comparison is `distance < minimum`, so exactly 15.0 km passes.

### D3. Road coverage is a gap rule per road

The design states the rule twice: "the next settlement of any kind is at most 75 km away" and "from any point, travelling in either direction reaches a settlement within 75 km". Both mean that consecutive settlements along a road are at most 75 km apart. A nearest-settlement distance would allow 150 km gaps, so it is not used.

For each road `(first, second, cells)`:

1. Settlement positions are index 0, the last index, every index whose cell is the first or last cell of any road of the input, and every index whose cell equals the cell of a place with `kind in SMALL_KINDS`. A road's ends are gate approach cells or village cells, so an end cell of another road marks a settlement this road passes: the reuse factor merges roads, and a trunk can run through the gate approach of a town it does not end at.
2. Step length is 1 for a cardinal step and `math.sqrt(2)` for a diagonal one.
3. For each pair of consecutive settlement positions `i < j`, the gap length is the sum of the step lengths from `i` to `j`.
4. A gap longer than `road_gap_max_km + 1e-9` is `road_gap`, subject `f"{first}--{second}"`, message with the two cells and the length to one decimal.

An elven village is never a settlement position: its kind is not in `SMALL_KINDS` and it is never a road end.

Alternative considered: a graph search from every road cell in every direction. Rejected: it costs a search per cell and gives the same answer, because every road ends at settlements.

### D4. Completed areas

A gap is checked only when every cell of the gap, both ends included, lies in some completed area. A cell lies in an area when `region_of(cell) == area.region` and, if `bounds` is set, the cell is inside the inclusive rectangle.

A gap that crosses an area boundary is therefore deferred until the areas on both sides are complete. Checking it earlier would demand a settlement exactly on the boundary.

`tools/settlement_spacing_areas.json` holds the list and ships as:

```json
{"areas": []}
```

An entry is `{"id": "<text>", "region": "<region key>", "bounds": [x_min, y_min, x_max, y_max]}` with `bounds` optional. `load_areas` rejects an unknown key, a non-list `areas`, a `bounds` that is not four integers with `x_min <= x_max` and `y_min <= y_max`, and a duplicate `id`, by raising `ValueError` naming the entry. `build_input` also rejects a region the continent does not declare.

An empty list checks no gap. `road-coverage-area-removal` later removes the list so that every gap is checked.

### D5. Placement identity rules

For each place with `kind in SMALL_KINDS`:

| Code | Condition |
| --- | --- |
| `id_prefix` | a village ID does not start with `village_`, or a hamlet ID does not start with `hamlet_` |
| `missing_lore` | `has_lore` is false |
| `no_nation` | `region_nation[region_of(cell)]` is `None` |
| `nation_mismatch` | lore nation differs from the region's nation (skipped when `no_nation` or `missing_lore` applies) |
| `population_range` | lore population is `None` or outside the kind's inclusive range |
| `forbidden_region` | `region_of(cell)` is in `forbidden_regions` |
| `village_off_road` | a village's cell is on no road of the input |

For every place of any kind:

| Code | Condition |
| --- | --- |
| `id_prefix` | the ID starts with `village_` or `hamlet_` and the kind is not the matching one |
| `duplicate_name` | two places share `display_name_zh`; reported once, subject the smaller ID, message naming the other |

The nation of a cell is the `nation_key` of its region. This is the reading of "the nation of the national border that contains its cell": the continent draws borders as lines, and a region with no nation key (`central_mountains`, `north_deep_forest`) is the land outside every national border.

### D6. Exemption field

`_LOCATION` in `schema.py` gains:

```python
        "spacing_exemption": _str(required=False, max_length=256, non_blank=True),
```

`LocationDeclaration` gains `spacing_exemption: str | None = None`, filled from `value.get("spacing_exemption")`. YAML:

```yaml
  hamlet_border_watch:
    kind: hamlet
    ...
    spacing_exemption: Border post beside the bridge town; the garrison lives outside the walls.
```

The reason is English, like `description` and `geographic_constraint`.

### D7. Command

```console
uv run --locked python -m tools.settlement_spacing [--root DIR] [--lore FILE] [--roads FILE] [--areas FILE]
```

- `--root` defaults to the repository root; `--roads` to `<root>/world/maps/data/road_network.json`; `--areas` to `tools/settlement_spacing_areas.json`; `--lore` to the shipped lore through `load_lore(None)`.
- `build_input` loads the world with `load_authoring_world(discover_source_documents(root))`, the terrain with `terrain_definition(world.continent)`, and the roads with `decode_road_network`.
- Output: one line per problem, `<code> <subject>: <message>`, then `spacing: N problems`.
- Exit 0 with no problem, 1 with any, 2 when the sources, the artifact, the lore override or the area file do not load (the error is printed to stderr).
- The command writes no file.

### D8. CI

Add to the preflight job of `.github/workflows/quality-gate.yml`, directly after "Validate road network freshness":

```yaml
      - name: Validate settlement spacing
        run: uv run --locked python -m tools.settlement_spacing
```

Add a test to `tests/test_quality_gate_contract.py` beside `test_preflight_checks_the_road_network_after_the_reference_context`, asserting the step's command and that it follows the road freshness step.

### D9. Tests

`tests/test_settlement_spacing.py`, a `unittest.TestCase` module with synthetic inputs only, registered in shard `top-level-4` of `.github/top-level-shards.json`. A small helper builds a `SpacingInput` whose `region_of` is a lambda over the x coordinate. The module covers every scenario of `specs/settlement-spacing/spec.md`; the command scenarios run `main` against a temporary directory that holds a minimal synthetic source set built with `packages/map-core/tests/authoring_fixtures.py`, as `tests/test_road_network_generation.py` does, plus an artifact written with `encode_road_document`.

The exemption field's schema scenario goes in `packages/map-core/tests/test_authoring.py`.

Do not add `covers_requirement` to these tests; every requirement here is ADDED. List them in the hand-off.

### D10. Documentation

- `.agents/skills/map-data-authoring/references/locations-and-districts.md`: add a section "Spacing rules for villages and hamlets" with the three rules of D2 and D3, the `spacing_exemption` field of D6 and the command of D7.
- `.agents/skills/map-data-authoring/references/verification.md`: add the command after the road network lines.
- `docs/development/map-authoring-documents.md`, the `locations.<id>` field list near line 83: add the optional `spacing_exemption`. `tests.test_map_authoring_contract` reads this document, so task 3.3 runs it.

## Risks / Trade-offs

- [A long road stretch in a region with no nation could never be covered] → Measured at design time on the committed artifact: no road cell lies in `central_mountains` or `north_deep_forest`.
- [The gap rule ignores a hamlet standing one cell beside the road] → Intended. The design counts only settlements on the road; an off-road hamlet does not shorten a road stretch.
- [The area file is tool data outside `content/maps`] → Intended. It is a temporary list that `road-coverage-area-removal` deletes, and `content/maps` accepts only declared document kinds.
