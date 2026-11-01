# Proposal

## Why

Specs and tests should regulate logic, not authored game data. `world.maps.tests.test_wilderness_geography_contract` now fails two tests on master. Commit efa4c607 moved `capital_valhalla` and `capital_grandia` in `content/maps/locations.yaml`, and two tests pin where those sites sit: the principal border-river ford must lie within 5 cells of the Altoria–Valhalla capital line, and Valhalla must lie within 15 rows of the forest edge. The same spec area also pins forest-edge mean rows, forest and nation area shares, a fixed ridge X band, hidden-valley distances and roster counts ("9 location targets and 6 harbours"). Commit 1bf6e0ad already invalidated some of those counts. Commit 1bf6e0ad also added the `city`/`town`/`port` location kinds and the `settlement` world-map wire kind, but no spec states them. The anchor requirement's title and scenarios still list only capitals, elven villages and dungeons.

## What Changes

- Remove the capital and principal border-ford position assertions. Delete `test_anchor_relationships_to_the_forest_edge` and the "principal ford on the capital line" check. Remove the matching spec text: Valhalla south of the forest edge, Eolas/Eternal Night in deep forest, Ciaran/Fionnen flanks, and the capital-to-capital route.
- Remove the other wilderness-geography data pins from the same spec and test module:
  - forest-edge mean row ≈1920, the count of distinct edge rows and the 20 % forest share;
  - nominal nation shares 0.43/0.30/0.27 and the copied effective territory shares;
  - the X1300–1520 ridge band and the "zero passes" assertion;
  - hidden-valley 30 km / 20 km clearance, which has no test;
  - the "waterways and their fords remain unchanged" clause;
  - the `capital_altoria` region pin and the "Nine anchors" / "Six harbor sites" / "9 location targets and 6 harbours" counts;
  - pinned probe coordinates such as `(900, 1042)`, `(900, 2350)`, `(700, 1960)`, row 1410 and the fixed X sample columns.
- Keep and restate the logic behind those pins, now derived from the authored data instead of copied from it:
  - every non-ford land cell on a waterway is impassable inland water, and every ford is walkable land on its own river;
  - west of the river source, the two banks beside a ford connect only through declared fords, and any single ford is enough;
  - every authored location and harbour is walkable and in one connected component;
  - each nominal claim agrees with its region's declared nominal nations;
  - every stem row outside the declared pass rows is blocked by a closed wall at its centre;
  - classifier and claim flips are checked at columns derived from the river's own span.
- Fix drift from commit 1bf6e0ad:
  - rename the lore-registries anchor requirement so it no longer lists only three kinds;
  - require that the map-core `LOCATION_KINDS` vocabulary and `AnchorKind` are the same closed set;
  - specify the world-map place classification: `capital` for capitals, `settlement` for the other public kinds, `hidden` for elven villages and dungeons, and `harbour` for harbour sites.
- Reshape the tests that commit 1bf6e0ad added or edited. `test_every_supported_kind_appears_without_a_fixed_roster_count` fails when content stops using a kind, so it becomes a vocabulary-agreement test plus a synthetic per-kind composition test. `test_national_settlements_carry_nation_and_population` keeps its reference checks (registered nation, positive population, no floors). It drops the authored-magnitude comparison "population below the nation's capital". Both tests gain `@covers_requirement`.
- No runtime code changes. Only specs and tests change. Pre-release project, so there is no compatibility layer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `wilderness-terrain`: two requirements are re-identified (REMOVED old ID, ADDED new name), because OpenSpec refuses to drop a scenario under MODIFIED:
  - "region_for_coordinates is a pure, deterministic function covering the whole bounded map" becomes "The coordinate classifier is a pure deterministic function over the whole bounded map". The `capital_altoria` region scenario is gone and the other scenarios are unchanged.
  - "Terrain and political control follow authored geography" becomes "Terrain and political control derive from authored geography", with derived invariants and no site, share or count pins.
  - MODIFIED: "The border river controls western crossing and classification": the fords scenario no longer names capitals.
  - MODIFIED: "The physical ridge is a continuous forked barrier": the scenario "No direct cross-range land route" is derived from the stem and its declared pass rows instead of an X band.
- `lore-registries`: "Anchor registry covers capitals, elven villages, and known dungeons" is REMOVED and ADDED as "Anchor registry composes every declared location kind". It adds the closed vocabulary shared with the map schema and the national-settlement lore join, and drops the "exactly nine anchors" scenario.
- `continental-geography`: "The known continent has frozen geographic declarations" is REMOVED and ADDED as "Known continent geographic declarations are frozen". The behavior is the same; the "Nine geographic anchors" / "Six reserved harbor sites" scenario titles lose their counts.
- `webclient-world-map`: MODIFIED: "World scope reveals only common geography and permitted district knowledge" gains the place-kind classification scenario.

## Impact

- Tests: `world/maps/tests/test_wilderness_geography_contract.py` (main edit), `world/lore/tests/test_anchors.py`, `web/webclient/presentation/tests/test_world_map.py`. Only `covers_requirement` IDs change in `world/maps/tests/test_wilderness_provider.py`, `world/lore/tests/test_anchor_placement.py` and `world/lore/tests/test_wilderness_regions.py`. No production module, content file, protocol document or shard manifest changes.
- Traceability: each of the four re-identified requirements gets a new ID. During apply, tests keep the old IDs, which are the only ones in `openspec/specs/`. The archive commit syncs the delta and re-anchors the literal IDs together (tasks.md "Workflow follow-up"), so traceability is never red on a committed state; see design D6.
- Test-data ledger: the `Data-contract test:` first docstring lines stay unchanged, so `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` need no edit.
- After this change, editing authored map coordinates, fords, river routes, harbour or location rosters, or forest-edge vertices only needs spec or test edits when it breaks a stated invariant, such as an unreachable site or a ford off its river.

### Open questions (borderline data pins deliberately left out of scope)

1. `test_river_cells_block_steps_and_the_ford_permits_the_crossing` uses `fords[1]`, which needs at least 2 fords. It also assumes a ford-free stretch of 40 columns east of that ford, and that the river stays inside a ±30-row box. These are data assumptions, but the test checks movement logic. Should a follow-up derive the probe columns and the box from the raster?
2. `world/lore/tests/test_nations.py` and continental-geography "Population and territory targets preserve authored settlement scale" pin national populations, territory shares and the 800k/600k/400k capital populations. lore-registries "Nation registry covers the three states" pins exactly three nations. These are lore data, not map data, and need a separate decision.
3. continental-geography "Coordinate frames have explicit physical units" pins a 2700 × 2700 frame. `frame_cells` is authored in `continent.yaml`. Is the frame size a design constant or data?
4. `tools/map-editor/frontend/src/components/ContinentInspector.vue` repeats `LOCATION_KINDS` by hand. No spec or test ties it to the schema. Should the editor get the kinds from the schema it already loads?
5. wilderness-map-provider says the mainland shoelace area is "exactly 5,000,000 km²", and `world/lore/tests/test_wilderness_regions.py` pins that value plus `is_on_mainland(1000, 1000)` / `not is_on_mainland(0, 0)`. Moving one coastline vertex breaks these. This is the same kind of pin as the two failures, but it sits in the mainland-provider capability. Fix it in a follow-up?
6. `world/lore/tests/test_anchor_placement.py` pins settlement-local entrance coordinates such as (3500, 2850). This is settlement map data rather than continent data.
7. The contract module keeps fixed probe literals that are not authored data: description sample cells, `range(150, 2200, 97)`, `source[0] + 50` and the 10-row bend tolerance. They hold only while the river and corridor keep their general shape. Should they be derived later? Once the module holds almost no authored data, its `Data-contract test:` ledger entry could also be retired.
8. lore-registries subrace scenarios name fixed entries (fionnen/ciaran/eolas, "seven beastfolk subspecies"). This is outside the map area and is not touched here.
