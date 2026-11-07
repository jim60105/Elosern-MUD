# Proposal

## Why

`road-network-generation` commits the road artifact, but the game ignores it: `area_map.py` hardcodes `"road": False` and `wilderness_terrain` reads regions only. The approved design `docs/superpowers/specs/2026-11-07-official-roads-design.md` makes roads visible on the area and travel maps and faster to walk.

## What Changes

- New read view `world/maps/road_network.py` with constant-time road cell lookup.
- `world/maps/runtime.py` rejects a candidate world whose road artifact is missing, corrupt or stale, and publishes the decoded network in the `MapWorld` bundle. Startup step `map_world_adoption` reaches this through `adopt()`. The runtime never computes the network.
- `world.rules.travel_cost.wilderness_terrain` returns `road` when both ends of a step are road cells. Planning, prediction and charging all read this function, so routes find roads with no separate routing rule.
- `web/webclient/presentation/area_map.py` publishes the real `road` fact, and its fact cache distinguishes road networks.
- Test fixtures that swap a synthetic domain into the published bundle clear the shipped road cells, so synthetic movement tests never depend on shipped data.

Non-goals: generation, the web client (`travel-paint.js` already draws road cells), world map display, a map editor layer, a "prefer roads" routing rule, and any change to walkability, river passability, region prose, the district partition or elevation data.

## Capabilities

### New Capabilities

- `wilderness-roads`: adoption of the road artifact, road cell lookup, road step terrain and the published road map fact.

### Modified Capabilities

None. `wilderness-travel-planning` and `movement-cost-charging` already specify duration-weighted routing and the road speed; their requirements hold unchanged.

## Impact

- Code: new `world/maps/road_network.py`; `world/maps/runtime.py`; `world/rules/travel_cost.py`; `web/webclient/presentation/area_map.py`.
- Test fixtures: `world/tests/geography_fixture.py`, `world/tests/synthetic_data/install.py`, `world/tests/synthetic_data/patching.py`, `web/browser_support/browser_fixtures_data/grafting.py`, `world/maps/tests/_editor_adoption_fixtures.py`, `world/maps/tests/test_runtime_adoption.py`, `world/maps/tests/test_runtime_adoption_rollback.py`.
- Tests: new `world/maps/tests/test_road_network_runtime.py`, `world/rules/tests/test_road_terrain.py`; `web/webclient/presentation/tests/test_area_map/test_wilderness_content.py`; new independence case in `tests/test_road_network_format.py`.
- Generated data: `content/map-reference-context.json` is regenerated, because its manifest hashes `world/rules/` sources.
- CI manifest: `.github/evennia-shards.json`.
- Dependencies: none added.
- Player impact: a road cell step now takes road time, and adoption fails until a stale artifact is regenerated.
- Human-reviewed, not test-established: how roads read on the travel and area maps at 1451x790 and 2560x1440. The review is recorded in the named review document `docs/development/road-network.md`, section "Human review record". It does not block this change.

## Batch:

Part of the official roads batch.

depends-on: road-network-generation

Code-conflict notes: requires `world/maps/data/road_network.json` from `road-network-generation`, and through it the codec and `travel_cost.region_speeds_m_per_hour` from `road-network-format`. All three regenerate `content/map-reference-context.json`, so apply them in order.
