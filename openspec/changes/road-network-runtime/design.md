# Design

## Context

See `proposal.md` for motivation. `docs/superpowers/specs/2026-11-07-official-roads-design.md` is the approved design. `road-network-format` provides `elosern_map_core.roads_codec`, `AuthoringWorld.road_network` and `travel_cost.region_speeds_m_per_hour`, and `road-network-generation` provides `world/maps/data/road_network.json`.

Code facts that shape this design:

- `map_world_adoption` is a startup step name in `server/conf/at_server_startstop.py`, not a symbol in `world/maps/runtime.py`. The step calls `adopt()`, which calls `load_candidate()`. The gate goes in `load_candidate`, beside the elevation gate.
- `world/tests/geography_fixture.py::publish_shipped_map_world` calls `runtime.adopt()`, and `publish_geography` and `publish_settlements` use `replace(runtime.current(), ...)`. Without a change, synthetic geography would inherit the shipped road cells, and a synthetic step could turn into a road step whenever the network is regenerated.
- `_TerrainOracle` in `area_map.py` caches facts across requests keyed by the elevation fingerprint and footprints, and reads roads nowhere yet.
- `travel_capacity.py:263` calls `wilderness_terrain(origin, origin)`, and `travel_cost.py:841` prices a gate approach step through `wilderness_step_cost`. Both go through the changed function.

## Goals / Non-Goals

**Goals:** the Integration section of the approved design, with test isolation from shipped road cells.

**Non-Goals:** do not change `world/maps/district_partition.py`, `world/rules/travel_plan.py`, `world/rules/travel_capacity.py`, `tools/road_network.py`, anything under `web/webclient-app/` or `tools/map-editor/`. Do not add a road preference to the planner. Do not include `road` in `_overview_fact`: the world map and district overview stay road-free.

## Decisions

### D1. Read view

New `world/maps/road_network.py`, with no NumPy, SciPy or generator import:

```python
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = Path(__file__).resolve().parent / "data" / "road_network.json"

_CURRENT: RoadNetwork | None = None

def _install(network: RoadNetwork | None) -> None: ...
def current() -> RoadNetwork | None: ...
def is_road_cell(cell: tuple[int, int]) -> bool: ...          # False when nothing is published
def road_cells() -> frozenset[tuple[int, int]]: ...            # empty when nothing is published
def artifact_metadata() -> RoadMetadata: ...                   # read_road_metadata(DATA_PATH text)
@cache
def frozen_network() -> RoadNetwork: ...                       # decode_road_network(DATA_PATH text)
def source_signature(world: AuthoringWorld, elevation_fingerprint: str) -> str | None: ...
```

`source_signature` returns `None` when `world.road_network is None`. Otherwise it returns `road_source_signature(world.fingerprints, elevation_fingerprint=elevation_fingerprint, region_speeds=travel_cost.region_speeds_m_per_hour())`, importing `travel_cost` inside the function.

`is_road_cell` is a set membership test on `tuple(cell)`. Unlike `elevation.current()`, an unpublished network answers false instead of raising: `wilderness_terrain` runs in many consumer tests and offline bundles that carry no network, and an ungated bundle truly has no adopted road. The artifact is always read from the repository's `DATA_PATH`, as the partition is, so a candidate root under test is compared against the committed artifact.

### D2. Adoption gate

`world/maps/runtime.py`:

```python
def road_freshness_for(world: AuthoringWorld, elevation_fingerprint: str) -> RoadFreshness:
    """The committed road artifact's freshness against this candidate's inputs."""
    from world.maps import road_network
    return road_freshness(
        road_network.artifact_metadata(),
        road_network.source_signature(world, elevation_fingerprint),
    )
```

In `load_candidate`, directly after the elevation `try` block:

```python
from elosern_map_core.roads_codec import RoadDocumentError
from world.maps import road_network

try:
    if not road_freshness_for(world, elevation_runtime.fingerprint).current:
        raise MapWorldError([
            "road network artifact is not current; run: "
            "uv run --locked python -m tools.road_network"
        ])
    roads = road_network.frozen_network()
except (OSError, RoadDocumentError) as error:
    raise MapWorldError([f"road network artifact rejected: {error}"]) from error
```

`MapWorld` gains `roads: Any | None = None` after `elevation`. `identity` feeds `roads.fingerprint` into the digest in the same style as elevation. `_install` calls `road_network._install(world.roads)` and `_uninstall` calls `road_network._install(None)`. `load_candidate` passes `roads=roads`. `compose`, `preview` and `ComposedWorld.map_world` leave it `None`, so offline producers stay ungated. Update the module docstring's step list.

Alternative rejected: reading the artifact from the candidate root. The artifact is a game output beside the partition, not a source.

### D3. Road terrain

`world/rules/travel_cost.py`:

```python
ROAD_TERRAIN = "road"

def wilderness_terrain(source_xy, destination_xy):
    """Road when both ends are road cells; otherwise the slower region's terrain."""
    from world.maps import road_network

    if road_network.is_road_cell(source_xy) and road_network.is_road_cell(destination_xy):
        return ROAD_TERRAIN
    ...  # existing body unchanged
```

Keep the import inside the function, like `wilderness_cell_size_m`: `world.rules` never imports `world.maps` at module scope. Add `ROAD_TERRAIN` to `__all__`. The rulebook's `road` row already exists, and `terrain_speed_m_per_hour` still rejects a missing row. `_route` already prices through this function, so `world/rules/travel_plan.py` needs no edit.

Two side effects are accepted and recorded here. `wilderness_terrain(origin, origin)` on a road cell makes the capacity estimate in `travel_capacity.py:263` use road speed for the whole estimate, which suits a party standing on a road. Two road cells that touch without being consecutive on one road also count as a road step, which is the design's "both ends" rule.

### D4. Map fact

`web/webclient/presentation/area_map.py`, `_TerrainOracle`:

- `__init__`: import `road_network`, set `self._roads = road_network.road_cells()`.
- Cache owners: `owners = (definition, sight.POLICY, road_network.current())`. The existing comparison is by identity and keeps the object alive, so a republished network never reuses cached facts, even when a synthetic network repeats a fingerprint. `None` compares equal to `None`.
- `_facts`: `"road": cell in self._roads`, and delete the stale comment above it.

Disclosure needs no code: unrevealed cells publish no facts, and `_overview_fact` keeps its own coarse fields.

### D5. Test isolation from shipped roads

Add `roads=None` to these `replace(...)` publications:

- `world/tests/geography_fixture.py`: `publish_geography`, `publish_settlements`.
- `world/tests/synthetic_data/install.py`: the `runtime.publish(` call that installs the kit.
- `world/tests/synthetic_data/patching.py`: `_apply_geography` and `_apply_settlements`.
- `web/browser_support/browser_fixtures_data/grafting.py`: the `_runtime.publish(` call in the graft.

Do not change `publish_districts`, `publish_interiors` or the restore paths: they do not alter terrain or gates, and restore paths must return the saved bundle unchanged.

Adoption tests that edit a settlement or location gain a matching road stub:

- `world/maps/tests/_editor_adoption_fixtures.py`: in both `regenerated_partition` and `generated_partition`, add `patch.object(runtime, "road_freshness_for", return_value=RoadFreshness(ROAD_ALGORITHM_VERSION, "t", True))` around the `yield`.
- `world/maps/tests/test_runtime_adoption.py` and `test_runtime_adoption_rollback.py`: wherever `partition_freshness_for` is patched to accept a candidate with an edited road input, patch `road_freshness_for` the same way. A test rejecting through an earlier gate needs no stub.

### D6. Traceability

Do **not** add `covers_requirement` in this change: `tools/spec_traceability.py` knows only IDs in `openspec/specs/`, so an annotation on an active-change requirement fails the gate. The hand-off lists the test-to-requirement mapping, and archive adds the annotations after sync.

## Risks / Trade-offs

- [A shipped-world test assumed regional terrain on a cell that is now a road] → Task 4.3 runs the non-browser suite once. Fix each failure by publishing that test's bundle with `roads=None` or by moving it to synthetic data, never by asserting shipped road cells.
- [Browser tests are not run by task 4.2] → Browser fixtures publish through the graft with `roads=None`, and CI owns the full browser suite.
- [`content/map-reference-context.json` hashes `world/rules/**/*.py`, so it goes stale here] → Task 4.2 regenerates it.
- [Editor saves make the artifact stale, and startup then refuses] → The rejection names the command. Editor regeneration is out of scope, matching the approved design. Authors follow `docs/development/road-network.md`.
- [Startup decodes the artifact on each process start] → It is a small JSON file, cached with `functools.cache`, as the partition is.

## Migration Plan

None. Persistent state does not change. Rollback is reverting the change; the artifact is then unused.
