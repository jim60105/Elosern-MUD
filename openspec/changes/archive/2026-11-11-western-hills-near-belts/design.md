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

**Goals:** near-belt habitat for western hills and valleys, using existing ordinary variants only.

**Non-Goals:** new species, sites, settlement birth policies, quest content, changes to the shipped zones, any validator or mechanism change, and copying any coordinate or count into documentation or tests.

## Decisions

### D1. Declarations (verbatim transcription)

The two snippet files in this change directory are the declarations. Copy them without editing any value:

- Block 1 of `snippets/monster_activity_rows.txt` (`ActivityArea` rows) goes at the end of `_ACTIVITY_AREA_DECLARATIONS` in `world/lore/monster_activity.py`.
- Block 2 of the same file (`MonsterActivity` rows) goes at the end of `_ACTIVITY_DECLARATIONS` in the same module.
- Block 1 of `snippets/monster_placement_rows.txt` (`EncounterComposition` rows) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS` in `world/lore/monster_placement.py`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS` in the same module.

Each block opens with a `# --- ... ---` marker line. Replace that marker with the one-line comment `# Near-settlement belts (western-hills-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.` and keep every row below it unchanged. Keys follow one grammar: `<zone>_grounds` for areas, `<zone>_<variant or suffix>` for compositions and `<composition>_activity` for activities.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement / road | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `capital_altoria_east_hinterland` | hinterland | `(867, 886, 1042, 1061)` | capital_altoria | 387 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `capital_altoria_west_hinterland` | hinterland | `(837, 856, 1040, 1059)` | capital_altoria | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_border_bridge_east_hinterland` | hinterland | `(823, 842, 1347, 1366)` | city_border_bridge | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_border_bridge_west_hinterland` | hinterland | `(802, 821, 1341, 1360)` | city_border_bridge | 381 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_confluence_east_hinterland` | hinterland | `(611, 630, 797, 816)` | city_confluence | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_confluence_west_hinterland` | hinterland | `(582, 601, 804, 823)` | city_confluence | 390 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_east_river_north_hinterland` | hinterland | `(1037, 1056, 1078, 1097)` | city_east_river | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_east_river_south_hinterland` | hinterland | `(1037, 1056, 1050, 1069)` | city_east_river | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_greyrock_east_hinterland` | hinterland | `(335, 354, 984, 1003)` | city_greyrock | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `city_greyrock_west_hinterland` | hinterland | `(307, 326, 984, 1003)` | city_greyrock | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `port_hills_mouth_hinterland` | hinterland | `(160, 179, 821, 840)` | port_hills_mouth | 397 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `port_west_ore_hinterland` | hinterland | `(207, 226, 684, 703)` | port_west_ore | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `port_westwind_hinterland` | hinterland | `(137, 156, 993, 1012)` | port_westwind | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_east_ferry_hinterland` | hinterland | `(1132, 1151, 1337, 1356)` | town_east_ferry | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_honey_vale_hinterland` | hinterland | `(1024, 1043, 675, 694)` | town_honey_vale | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_ruins_gate_hinterland` | hinterland | `(510, 529, 1119, 1138)` | town_ruins_gate | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_scarp_hinterland` | hinterland | `(1283, 1302, 693, 712)` | town_scarp | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_vineyard_hinterland` | hinterland | `(1001, 1020, 1145, 1164)` | town_vineyard | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `town_west_ferry_hinterland` | hinterland | `(431, 450, 1320, 1339)` | town_west_ferry | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `western_road_01` | corridor | `(1025, 1044, 506, 525)` | city_salt_road / town_honey_vale | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_02` | corridor | `(1186, 1205, 858, 877)` | city_east_river / town_scarp | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_03` | corridor | `(464, 483, 541, 560)` | city_confluence / city_salt_ferry | 400 | `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager` |
| `western_road_04` | corridor | `(674, 693, 1065, 1084)` | city_border_bridge / town_ruins_gate | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_05` | corridor | `(1151, 1170, 692, 711)` | town_honey_vale / town_scarp | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_06` | corridor | `(738, 757, 902, 921)` | capital_altoria / city_confluence | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_07` | corridor | `(556, 575, 690, 709)` | city_confluence / city_salt_ferry | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_08` | corridor | `(715, 734, 713, 732)` | city_confluence / town_honey_vale | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_09` | corridor | `(293, 312, 595, 614)` | city_salt_ferry / port_west_ore | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |
| `western_road_10` | corridor | `(923, 942, 687, 706)` | city_confluence / town_honey_vale | 400 | `cliff_stepper`, `burrow_maker`, `hanging_nest_forager` |

Each zone has exactly one rectangle, and that rectangle is also its grounds. Initialization fills each zone to its lower bound, and later waves restore that bound. That works out to about 2 individuals per 100 eligible hinterland cells and 1 per 100 eligible corridor cells. The probe's per-zone bounds are not recorded anywhere permanent.

### D3. Pools and aggression

Hinterland zones and the one non-remote corridor (`western_road_03`) use the low pool: `burrow_maker` 1, `mudbank_dweller` 1–2, `wax_cache_forager` 2–3 (cohesive) and `hanging_nest_forager` 2–3 (cohesive), all passive. The nine remote corridors use the mid pool: `cliff_stepper` 1 (the mid ordinary goat), with `burrow_maker` 1 and `hanging_nest_forager` 2–3 as low company, all passive. The goat binding stays passive, as it is in the shipped rockland zone. Hinterland densities are 2..4 and corridor densities 1..3, with cell capacity 3, wave budget 3 and 3600/600 timing. No pool names `flock_leader`, `nest_guard`, `reef_warden`, `pass_warden`, `trail_hunter`, `bay_warden` or any high-tier variant. The passive bindings near towns keep the light-adventure tone of `docs/lore/monster-creation-guidelines.md` §5: a hinterland individual answers only after engagement.

### D4. Human-review documentation

Add a subsection `### Near-settlement belts: western hills and valleys` under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, after the section's last existing subsection and before `## Assertion roles and requirement mapping`. It holds:

1. One paragraph naming the belts this change adds (hinterland beside inhabited settlements, and road corridors). It states that the declarations are the only authority and repeats no coordinate, density, count or timing.
2. One paragraph on species fit. The quarries, transport lanes and scrub around the hill towns suit the goblin and the rat. The hare and the slime cover valley fields and channels. The goat appears only on remote hill roads, so the ground just outside every town stays low tier.
3. One paragraph on tiers. No stronger or high-tier variant joins an ordinary pool, and settlement surroundings hold only low-tier passive individuals.
4. A verification table listing the commands in the Verification section and their observed results.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then rerun it with `--check`.

## Risks / Trade-offs

- [Each fresh provisioning creates more individuals, which lengthens startup and every test that provisions the shipped wilderness through `world.tests.geography_fixture.sync_test_wilderness`] → record the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` in the D4 verification table as a non-gating observation. Nothing gates on it.
- [A rectangle reads wrong to a reviewer] → it can be moved later under the same rules with no test edit. Move the zone rectangle and its grounds together.
- [Existing development worlds refuse at startup] → reset them as described in `docs/development/database-reset.md` (pre-release).

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each of these labels on its own with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_content_expansion_sites`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change western-hills-near-belts` and `openspec validate western-hills-near-belts --strict`.
