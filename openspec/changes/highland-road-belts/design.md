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

**Goals:** near-belt habitat for northwest highland forest roads, using existing ordinary variants only.

**Non-Goals:** new species, sites, settlement birth policies, quest content, changes to the shipped zones, any validator or mechanism change, and copying any coordinate or count into documentation or tests.

## Decisions

### D1. Declarations (verbatim transcription)

The two snippet files in this change directory are the declarations. Copy them without editing any value:

- Block 1 of `snippets/monster_activity_rows.txt` (`ActivityArea` rows) goes at the end of `_ACTIVITY_AREA_DECLARATIONS` in `world/lore/monster_activity.py`.
- Block 2 of the same file (`MonsterActivity` rows) goes at the end of `_ACTIVITY_DECLARATIONS` in the same module.
- Block 1 of `snippets/monster_placement_rows.txt` (`EncounterComposition` rows) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS` in `world/lore/monster_placement.py`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS` in the same module.

Each block opens with a `# --- ... ---` marker line. Replace that marker with the one-line comment `# Near-settlement belts (highland-road-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.` and keep every row below it unchanged. Keys follow one grammar: `<zone>_grounds` for areas, `<zone>_<variant or suffix>` for compositions and `<composition>_activity` for activities.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement / road | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `highland_road_01` | corridor | `(908, 927, 1827, 1846)` | capital_valhalla / city_tiger_roar | 400 | `wood_stalker` |
| `highland_road_02` | corridor | `(540, 559, 1784, 1803)` | capital_valhalla / city_moon_howl | 400 | `wood_stalker` |
| `highland_road_03` | corridor | `(257, 276, 1631, 1650)` | city_horn_plain / city_shadow_wood | 400 | `wood_stalker` |
| `highland_road_04` | corridor | `(487, 506, 1537, 1556)` | city_horn_plain / city_swift_wind | 400 | `wood_stalker` |
| `highland_road_05` | corridor | `(800, 819, 1548, 1567)` | city_mutual_market / city_swift_wind | 400 | `wood_stalker` |
| `highland_road_06` | corridor | `(977, 996, 1434, 1453)` | town_grizzly / town_pine_ferry | 400 | `wood_stalker` |
| `highland_road_07` | corridor | `(784, 803, 1769, 1788)` | capital_valhalla / city_tiger_roar | 400 | `wood_stalker` |
| `highland_road_08` | corridor | `(620, 639, 1706, 1725)` | capital_valhalla / city_moon_howl | 391 | `wood_stalker` |

Each zone has exactly one rectangle, and that rectangle is also its grounds. Initialization fills each zone to its lower bound, and later waves restore that bound. That works out to about 2 individuals per 100 eligible hinterland cells and 1 per 100 eligible corridor cells. The probe's per-zone bounds are not recorded anywhere permanent.

### D3. Pools and aggression

Each corridor holds one composition, `wood_stalker` 1 (solitary roaming, `contact`, the shipped lynx binding), with densities 1..3, capacity 3, budget 3 and 3600/600 timing. The region does not yet have enough species for 3–5 compositions per pool. No pool names `flock_leader`, `nest_guard`, `reef_warden`, `pass_warden`, `trail_hunter`, `bay_warden` or any high-tier variant. The passive bindings near towns keep the light-adventure tone of `docs/lore/monster-creation-guidelines.md` §5: a hinterland individual answers only after engagement.

### D4. Human-review documentation

Add a subsection `### Near-settlement belts: northwest highland forest roads` under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, after the section's last existing subsection and before `## Assertion roles and requirement mapping`. It holds:

1. One paragraph naming the belts this change adds (hinterland beside inhabited settlements, and road corridors). It states that the declarations are the only authority and repeats no coordinate, density, count or timing.
2. One paragraph on species fit. The lynx dossier ties the animal to hunting trails and pack-animal routes, and the remote stretches of the highland trunk roads are exactly that. Every rectangle lies at least 80 cells from any settlement, so no ground near a town gets a mid-tier birth.
3. One paragraph on tiers. No stronger or high-tier variant joins an ordinary pool, and settlement surroundings hold only low-tier passive individuals.
4. One paragraph on the deferral: None of the region's 18 settlements gets a hinterland zone in Wave 1. Hinterland pools are low-tier only, and the region has no low-tier species until its own species wave. Corridor points within 80 cells of a settlement are left unused for the same reason.
5. A verification table listing the commands in the Verification section and their observed results.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then rerun it with `--check`.

## Risks / Trade-offs

- [Each fresh provisioning creates more individuals, which lengthens startup and every test that provisions the shipped wilderness through `world.tests.geography_fixture.sync_test_wilderness`] → record the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` in the D4 verification table as a non-gating observation. Nothing gates on it.
- [A rectangle reads wrong to a reviewer] → it can be moved later under the same rules with no test edit. Move the zone rectangle and its grounds together.
- [Existing development worlds refuse at startup] → reset them as described in `docs/development/database-reset.md` (pre-release).

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each of these labels on its own with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_content_expansion_sites`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change highland-road-belts` and `openspec validate highland-road-belts --strict`.
