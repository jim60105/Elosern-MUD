# Design

## Context

See proposal.md (Why). Facts at `9b67edf2`:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `population-zone-pass-indexing` (merged at `3756992d`) makes one boundary zone pass read the state record once and scan presence once, so the boundary cost of the larger zone set grows linearly.
- Planning probe, run while writing this proposal against `9b67edf2` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). Neither world/lore nor the map content has changed since. With every Wave 1 zone loaded together (the 9 shipped zones plus this change's rectangles and the rectangles of the sibling placement changes), `validate_ecology_geometry(...)` returned `()` and `activity_area_problems` reported nothing for any new grounds. Import-time validation also accepted every row. The eligible-cell column below is the probe's `eligible_birth_cells` count. It is a planning input and is not copied into documentation or tests.
- Belt rules the probe applied:
  - Hinterland rectangle: 20×20, nearest edge 3–8 cells (Chebyshev) from the settlement footprint, at least 4 cells from every other settlement footprint, at least 2 cells from every other zone, activity area and site grounds, and at least 340 of its 400 cells valid cells of the settlement's region. Capitals and cities get two rectangles on different sides.
  - Corridor rectangle: 20×20, 3 cells from a road cell of `world/maps/data/road_network.json`, at least 30 cells from any settlement and at least 45 cells from any other zone. Sides alternate within a region, and a corridor point at least 80 cells from every settlement counts as remote.

## Goals / Non-Goals

**Goals:** near-belt habitat for eastern plains, using existing ordinary variants only.

**Non-Goals:** new species, sites, settlement birth policies, quest content, changes to the shipped zones, any validator or mechanism change, and copying any coordinate or count into documentation or tests.

## Decisions

### D1. Declarations (verbatim transcription)

The two snippet files in this change directory are the declarations. Copy them without editing any value:

- Block 1 of `snippets/monster_activity_rows.txt` (`ActivityArea` rows) goes at the end of `_ACTIVITY_AREA_DECLARATIONS` in `world/lore/monster_activity.py`.
- Block 2 of the same file (`MonsterActivity` rows) goes at the end of `_ACTIVITY_DECLARATIONS` in the same module.
- Block 1 of `snippets/monster_placement_rows.txt` (`EncounterComposition` rows) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS` in `world/lore/monster_placement.py`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS` in the same module.

Each block opens with a `# --- ... ---` marker line. Replace that marker with the one-line comment `# Near-settlement belts (eastern-plains-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.` and keep every row below it unchanged. Keys follow one grammar: `<zone>_grounds` for areas, `<zone>_<variant or suffix>` for compositions and `<composition>_activity` for activities.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement / road | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `capital_grandia_east_hinterland` | hinterland | `(1961, 1980, 1251, 1270)` | capital_grandia | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `capital_grandia_west_hinterland` | hinterland | `(1930, 1949, 1251, 1270)` | capital_grandia | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_imperial_ferry_east_hinterland` | hinterland | `(1992, 2011, 1115, 1134)` | city_imperial_ferry | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_imperial_ferry_west_hinterland` | hinterland | `(1964, 1983, 1115, 1134)` | city_imperial_ferry | 397 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_spice_road_east_hinterland` | hinterland | `(1981, 2000, 506, 525)` | city_spice_road | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_spice_road_west_hinterland` | hinterland | `(1953, 1972, 506, 525)` | city_spice_road | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_starglow_east_hinterland` | hinterland | `(2036, 2055, 958, 977)` | city_starglow | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_starglow_west_hinterland` | hinterland | `(2008, 2027, 945, 964)` | city_starglow | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_twin_currents_east_hinterland` | hinterland | `(2072, 2091, 699, 718)` | city_twin_currents | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_twin_currents_west_hinterland` | hinterland | `(2044, 2063, 691, 710)` | city_twin_currents | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_wheatwave_east_hinterland` | hinterland | `(2087, 2106, 1512, 1531)` | city_wheatwave | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `city_wheatwave_west_hinterland` | hinterland | `(2059, 2078, 1512, 1531)` | city_wheatwave | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `port_dawnlight_hinterland` | hinterland | `(2452, 2471, 1507, 1526)` | port_dawnlight | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `port_tide_wind_hinterland` | hinterland | `(2559, 2578, 1144, 1163)` | port_tide_wind | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_black_soil_hinterland` | hinterland | `(1628, 1647, 1412, 1431)` | town_black_soil | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_crystal_hinterland` | hinterland | `(1876, 1895, 1617, 1636)` | town_crystal | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_east_pasture_hinterland` | hinterland | `(2305, 2324, 884, 903)` | town_east_pasture | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_emerald_lake_hinterland` | hinterland | `(1901, 1920, 890, 909)` | town_emerald_lake | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_maple_foot_hinterland` | hinterland | `(1649, 1668, 1235, 1254)` | town_maple_foot | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_north_wood_keep_hinterland` | hinterland | `(1820, 1839, 1869, 1888)` | town_north_wood_keep | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_orange_blossom_hinterland` | hinterland | `(1810, 1829, 502, 521)` | town_orange_blossom | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_silver_ridge_hinterland` | hinterland | `(1525, 1544, 745, 764)` | town_silver_ridge | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_steed_plain_hinterland` | hinterland | `(1692, 1711, 848, 867)` | town_steed_plain | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_sunken_bell_hinterland` | hinterland | `(2229, 2248, 1707, 1726)` | town_sunken_bell | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `town_sunrise_hinterland` | hinterland | `(2399, 2418, 1448, 1467)` | town_sunrise | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_01` | corridor | `(2333, 2352, 676, 695)` | port_east_bay / town_east_pasture | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_02` | corridor | `(1617, 1636, 1040, 1059)` | town_maple_foot / town_steed_plain | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_03` | corridor | `(2206, 2225, 532, 551)` | city_twin_currents / port_east_bay | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_04` | corridor | `(2241, 2260, 1445, 1464)` | city_wheatwave / town_sunrise | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_05` | corridor | `(2481, 2500, 1308, 1327)` | port_tide_wind / town_sunrise | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_06` | corridor | `(1790, 1809, 1289, 1308)` | capital_grandia / town_maple_foot | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_07` | corridor | `(2419, 2438, 1035, 1054)` | port_tide_wind / town_east_pasture | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_08` | corridor | `(2170, 2189, 987, 1006)` | city_imperial_ferry / town_east_pasture | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_09` | corridor | `(2052, 2071, 1382, 1401)` | capital_grandia / city_wheatwave | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_10` | corridor | `(1655, 1674, 636, 655)` | town_orange_blossom / town_silver_ridge | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_11` | corridor | `(1849, 1868, 1741, 1760)` | town_crystal / town_north_wood_keep | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |
| `eastern_road_12` | corridor | `(1750, 1769, 1517, 1536)` | town_black_soil / town_crystal | 400 | `grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager` |

Each zone has exactly one rectangle, and that rectangle is also its grounds. Initialization fills each zone to its lower bound, and later waves restore that bound. That works out to about 2 individuals per 100 eligible hinterland cells and 1 per 100 eligible corridor cells. The probe's per-zone bounds are not recorded anywhere permanent.

### D3. Pools and aggression

Every eastern zone, hinterland and corridor alike, uses the same four low-tier ordinary compositions, because the region has no mid-tier species yet: `grain_pecker` 1–2 (solitary roaming, passive), `burrow_maker` 1 (solitary, passive), `mudbank_dweller` 1–2 (solitary, passive) and `wax_cache_forager` 2–3 (cohesive family, passive). All 12 corridor points are remote, and they still take the low pool for the same reason. Hinterland densities are 2..4 and corridor densities 1..3. All zones use cell capacity 3, wave budget 3 and the shared 3600/600 recovery timing. No pool names `flock_leader`, `nest_guard`, `reef_warden`, `pass_warden`, `trail_hunter`, `bay_warden` or any high-tier variant. The passive bindings near towns keep the light-adventure tone of `docs/lore/monster-creation-guidelines.md` §5: a hinterland individual answers only after engagement.

### D4. Human-review documentation

Add a subsection `### Near-settlement belts: eastern plains` under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, after the section's last existing subsection and before `## Assertion roles and requirement mapping`. It holds:

1. One paragraph naming the belts this change adds (hinterland beside inhabited settlements, and road corridors). It states that the declarations are the only authority and repeats no coordinate, density, count or timing.
2. One paragraph on species fit. Field margins, irrigation side-channels and grain stores lie just outside every eastern town, so the sparrow, hare, slime and rat fit the hinterland of a farming town. The slime's damp-cell deviation, already recorded under "Content expansion habitats", applies here too: each zone uses a bounded rectangle rather than individually damp cells.
3. One paragraph on tiers. No stronger or high-tier variant joins an ordinary pool, and settlement surroundings hold only low-tier passive individuals.
4. A verification table listing the commands in the Verification section and their observed results.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then rerun it with `--check`.

## Risks / Trade-offs

- [Each fresh provisioning creates more individuals, which lengthens startup and every test that provisions the shipped wilderness through `world.tests.geography_fixture.sync_test_wilderness`] → record the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` in the D4 verification table as a non-gating observation. Nothing gates on it.
- [A rectangle reads wrong to a reviewer] → it can be moved later under the same rules with no test edit. Move the zone rectangle and its grounds together.
- [Existing development worlds refuse at startup] → reset them as described in `docs/development/database-reset.md` (pre-release).

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each of these labels on its own with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_content_expansion_sites`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change eastern-plains-near-belts` and `openspec validate eastern-plains-near-belts --strict`.
