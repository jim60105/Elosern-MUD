# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 placement rows, `central-mountains-placement` and the planned Wave 1 and Wave 2 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)`, `WeightedComposition(composition_key, weight)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- `highland-road-belts` lands `highland_road_01` … `highland_road_08`, each with one rectangle, grounds `<zone>_grounds`, densities 1..3, capacity 3, budget 3, 3600/600 timing and a one-entry pool `WeightedComposition("<zone>_wood_stalker", 1)`. The new corridor compositions bind activities over those existing grounds.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `d1ac4b84` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). With the 9 shipped zones, every Wave 1 zone and site (with the eight corridor pools edited), every `central-mountains-placement` zone and site, and this change's rows loaded together, `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The Wave 1 and Wave 2 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. The eligible-cell column below is the probe's `eligible_birth_cells` count. It is a planning input and is not copied into documentation or tests.
- Belt rules the probe applied:
  - Hinterland rectangle: 20×20, nearest edge 3–8 cells (Chebyshev) from the settlement footprint, at least 4 cells from every other settlement footprint, at least 2 cells from every other zone, activity area and site grounds, and at least 340 of its 400 cells valid cells of the settlement's region. The capital and each city get two rectangles on different sides; each town gets one.
  - Deep-wild rectangle: 30×30, at least 70 cells from every settlement, at least 8 cells from every other zone, area and site grounds, and at least 120 cells from every other deep-wild rectangle.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region, at least 2 cells clear of every zone, area and other grounds, and at least 40 cells from every settlement (80 for the boss site).

## Goals / Non-Goals

**Goals:** the deferred hinterland belt for all 18 northwest settlements, low company on the Wave 1 corridors, the deep-wild belt and sites for the northwest highland forest.

**Non-Goals:** new corridor zones (corridor points within 80 cells of a settlement stay unused), edits to the `highland-road-belts` change directory, edits to any corridor rectangle, density or timing, settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- corridor low company activities ---` part, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- corridor low company ---` part, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.
- Block 4 of the same file is an edit, not an append. For each `# highland_road_NN: the pool becomes` entry, find the existing `EcologyZone` row whose key is `highland_road_NN` and replace its `pool` tuple (the fourth argument, today a one-entry tuple) with the listed three-entry tuple. Leave every other argument of the row unchanged and append no new row for these keys.

Replace each `# --- ... ---` marker of blocks 1–3 with a one-line comment that names this change and what follows: `# Northwest highland forest (northwest-highland-placement): ...`. Use "hinterland and deep-wild zones", "corridor low company" or "site compositions/extents/activities" as fits. Block 4's comment lines are instructions and are not copied. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `capital_valhalla_east_hinterland` | hinterland | `(718, 737, 1680, 1699)` | capital_valhalla | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `capital_valhalla_west_hinterland` | hinterland | `(688, 707, 1680, 1699)` | capital_valhalla | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_fox_fire_north_hinterland` | hinterland | `(1283, 1302, 1705, 1724)` | city_fox_fire | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_fox_fire_south_hinterland` | hinterland | `(1283, 1302, 1677, 1696)` | city_fox_fire | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_horn_plain_east_hinterland` | hinterland | `(396, 415, 1645, 1664)` | city_horn_plain | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_horn_plain_west_hinterland` | hinterland | `(368, 387, 1645, 1664)` | city_horn_plain | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_iron_claw_east_hinterland` | hinterland | `(1180, 1199, 1589, 1608)` | city_iron_claw | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_iron_claw_west_hinterland` | hinterland | `(1152, 1171, 1589, 1608)` | city_iron_claw | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_moon_howl_east_hinterland` | hinterland | `(474, 493, 1834, 1853)` | city_moon_howl | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_moon_howl_west_hinterland` | hinterland | `(446, 465, 1834, 1853)` | city_moon_howl | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_mutual_market_north_hinterland` | hinterland | `(821, 840, 1374, 1393)` | city_mutual_market | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_mutual_market_west_hinterland` | hinterland | `(800, 819, 1368, 1387)` | city_mutual_market | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_shadow_wood_east_hinterland` | hinterland | `(191, 210, 1567, 1586)` | city_shadow_wood | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_shadow_wood_north_hinterland` | hinterland | `(185, 204, 1588, 1607)` | city_shadow_wood | 381 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_swift_wind_east_hinterland` | hinterland | `(605, 624, 1424, 1443)` | city_swift_wind | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_swift_wind_west_hinterland` | hinterland | `(577, 596, 1424, 1443)` | city_swift_wind | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_tiger_roar_east_hinterland` | hinterland | `(1005, 1024, 1854, 1873)` | city_tiger_roar | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `city_tiger_roar_west_hinterland` | hinterland | `(977, 996, 1854, 1873)` | city_tiger_roar | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_ancestor_shrine_hinterland` | hinterland | `(734, 753, 1579, 1598)` | town_ancestor_shrine | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_east_ford_camp_hinterland` | hinterland | `(1133, 1152, 1370, 1389)` | town_east_ford_camp | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_falcon_hinterland` | hinterland | `(1098, 1117, 1439, 1458)` | town_falcon | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_frost_wind_hinterland` | hinterland | `(217, 236, 1797, 1816)` | town_frost_wind | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_grizzly_hinterland` | hinterland | `(901, 920, 1473, 1492)` | town_grizzly | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_pine_ferry_hinterland` | hinterland | `(1065, 1084, 1712, 1731)` | town_pine_ferry | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_shaman_cave_hinterland` | hinterland | `(1173, 1192, 1800, 1819)` | town_shaman_cave | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_stag_ferry_hinterland` | hinterland | `(374, 393, 1752, 1771)` | town_stag_ferry | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `town_west_ford_camp_hinterland` | hinterland | `(433, 452, 1352, 1371)` | town_west_ford_camp | 400 | `pine_floor_grouse`, `dam_builder`, `vein_digger` |
| `far_west_wild` | deep | `(150, 179, 1295, 1324)` | remote | 900 | `trapline_raider`, `wood_stalker`, `pine_floor_grouse`, `vein_digger` |
| `howl_ridge_wild` | deep | `(630, 659, 1895, 1924)` | remote | 881 | `trapline_raider`, `wood_stalker`, `pine_floor_grouse`, `vein_digger` |
| `pine_ferry_west_wild` | deep | `(885, 914, 1670, 1699)` | remote | 900 | `trapline_raider`, `wood_stalker`, `pine_floor_grouse`, `vein_digger` |
| `valhalla_north_wild` | deep | `(780, 809, 1880, 1909)` | remote | 900 | `trapline_raider`, `wood_stalker`, `pine_floor_grouse`, `vein_digger` |
| `valhalla_west_wild` | deep | `(540, 569, 1670, 1699)` | remote | 900 | `trapline_raider`, `wood_stalker`, `pine_floor_grouse`, `vein_digger` |

Belts: the 27 `*_hinterland` zones are the hinterland belt (densities 2..4). The five `*_wild` zones are 30×30 deep-wild zones (densities 1..2). Every new zone uses cell capacity 3, wave budget 3 and 3600/600 timing. The corridors `highland_road_01` … `highland_road_08` keep their Wave 1 rectangle, densities and timing; their pools become `wood_stalker`, `pine_floor_grouse` and `vein_digger`.

### D3. Pools, aggression and sites

- Hinterland pools: `pine_floor_grouse` 2–3 (cohesive lek group, passive), `dam_builder` 2–3 (cohesive family, passive) and `vein_digger` 1 (solitary, passive).
- Corridor low company: `pine_floor_grouse` 2–3 (cohesive, passive) and `vein_digger` 1 (solitary, passive) beside the shipped lynx composition.
- Deep-wild pools: `trapline_raider` 1 (solitary, `contact`), `wood_stalker` 1 (solitary, `contact`, the shipped lynx binding), and the low company `pine_floor_grouse` 2–3 and `vein_digger` 1 (passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `lek_master_lek` | camp | `(1050, 1520)` | `lek_master_lek_group` (`lek_master_cock` 1, `pine_floor_grouse` 2) | 3 | recoverable, 86400 | `lek_master_lek_lek` |
| `old_dam_keeper_dam` | nest | `(320, 1700)` | `old_dam_keeper_dam_group` (`old_dam_keeper` 1, `dam_builder` 2) | 3 | recoverable, 86400 | `old_dam_keeper_dam_pond` |
| `deep_seam_mole_den` | nest | `(1240, 1560)` | `deep_seam_mole_den_member` (`deep_seam_mole` 1) | 1 | recoverable, 86400 | `deep_seam_mole_den_chamber` |
| `winter_den_glutton_den` | nest | `(282, 1902)` | `winter_den_glutton_den_member` (`winter_den_glutton` 1) | 1 | recoverable, 86400 | `winter_den_glutton_den_cache` |
| `golden_plume_boss_site` | boss_site | `(290, 1440)` | `golden_plume_boss` (`windcrest_elder` 1) | 1 | one-shot, individual name 金翎 | `golden_plume_boss_cliff` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Near-settlement belts: northwest highland forest` after the last existing subsection. Write it without coordinates, densities or counts:

1. One paragraph on the belts: the hinterland beside 咆哮王城, every city and every town, which Wave 1 deferred; the deep-wild zones away from the settlements; and the unchanged corridor rectangles.
2. One paragraph on species fit: lekking grouse, ford beavers and ore-vein moles as passive low-tier company beside the beastfolk settlements, and the wolverine and the lynx on the remote ground with low company.
3. One paragraph on the corridor edit: the eight corridors keep the lynx and gain low-tier passive company, so a traveller meets more than one kind of animal on the trunk roads.
4. One paragraph on sites: the lek, the old dam, the deep mole chamber and the wolverine's snow cache as recoverable sites, and the one-shot griffin boss 金翎 on a remote ore cliff.
5. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [The pool edit touches rows another change lands] → the dependency on `central-mountains-placement` puts this change after `highland-road-belts` in the serial placement chain, and task 1.3 checks that each edited row gains exactly two pool entries.
- [27 hinterland zones and 5 deep-wild zones lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [Beaver families appear in hinterland zones the probe chose without consulting waterway cells] → the human review may drop `dam_builder` from a zone's pool that reads dry without any test edit.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change northwest-highland-placement` and `openspec validate northwest-highland-placement --strict`.
