# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned open placement rows (`north-deep-forest-placement`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement`, `southeast-coast-placement`) and the planned Wave 2, Wave 3 and Wave 4 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)`, `WeightedComposition(composition_key, weight)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- `coastal-near-belts` (landed, archived) declared `port_fishers_cove_hinterland`, `port_south_tide_hinterland` and `port_white_sail_hinterland` with the three-entry crab pool (`shore_walker`, `shore_walker_pair`, `shore_walker_trio`), and `southwest_road_01` and `southwest_road_02` with the same three crab entries, each with one rectangle and grounds `<zone>_grounds`. The new compositions bind activities over those existing grounds. The earlier `southwest_shore_habitat` (crab and `reef_warden`) stays as it is.
- The inland settlements `city_salt_ferry` (鹽津城, a city on the region's northern boundary), `city_salt_road` (鹽道城, a city) and `town_olive_ferry` (橄欖津, a town) have no zone yet; `docs/development/regional-monster-population.md` ("Near-settlement belts: both coasts", "Deferral") records why.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `cf4643a1` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). The landed registries, the rows parsed from the snippet files of the five open placement changes (with their pool edits applied) and this change's rows were loaded together; the not-yet-landed Wave 2, Wave 3 and Wave 4 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The eligible-cell, bound and water-adjacent columns below are probe outputs (a water-adjacent cell is a valid region cell with a non-land cell among its 8 neighbours). They are planning inputs and are not copied into documentation or tests. The gate at implementation time is the geometry check in the Verification labels, not this probe.
- Belt rules the probe applied:
  - Hinterland rectangle: 20×20, nearest edge 3–8 cells outside its settlement (every chosen rectangle sits at 4), at least 10 cells from every other settlement, at least 340 valid region cells and 280 eligible cells; two per city, one per town.
  - Corridor rectangle: 20×20, 3 cells from a road cell of `world/maps/data/road_network.json`, at least 30 cells from any settlement, and at least 45 cells (the three remote corridors) or 25 cells (the two corridors nearer a settlement) from any other zone. A corridor point at least 80 cells from every settlement counts as remote.
  - Deep-wild rectangle: 30×30, at least 70 cells from every settlement, at least 8 cells from every other zone, area and site grounds, at least 120 cells from every other new deep-wild rectangle, at least 12 water-adjacent cells (the shore-dossier rule) and at least 700 eligible cells. Five rectangles qualify at the 120-cell spacing other regions used.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region, at an edge distance of at least 2 cells (at least one free cell between) from every zone, area and other grounds, at least 40 cells from every settlement (80 for the boss site), and holding at least 10 water-adjacent cells (every site except the dry-ground ant mound).

## Goals / Non-Goals

**Goals:** the deferred inland hinterland belt, the new low species beside the ports and on the landed corridors, five more road corridors, the deep-wild belt and the sites of the south-west coast.

**Non-Goals:** edits to the archived `coastal-near-belts` directory, edits to any existing rectangle, density, capacity or timing, edits to `southwest_shore_habitat`, settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- activities of the compositions added to existing zones ---` part, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- compositions added to existing zones ---` part, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.
- Block 4 of the same file is an edit, not an append. For each `# <zone>: the pool becomes` entry, find the existing `EcologyZone` row whose key is `<zone>` and replace its `pool` tuple (the fourth argument, today a three-entry tuple) with the listed tuple. The listed tuple keeps the three existing entries in their order and appends the new ones. It replaces the existing tuple including its closing `),` line, so the row never contains `),,`. Leave every other argument of the row unchanged and append no new row for these keys. The three `port_*_hinterland` entries gain two `WeightedComposition` lines each; `southwest_road_01` and `southwest_road_02` gain one each.

Replace each `# --- ... ---` marker of blocks 1–3 with a one-line comment that names this change and what follows: `# South-west coast (southwest-coast-placement): ...`. Use "hinterland, road-corridor and deep-wild zones", "compositions added to the landed port hinterland and corridor zones" or "site compositions/extents/activities" as fits. Block 4's comment lines are instructions and are not copied. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor | Eligible birth cells (probe) | Bounds (probe) | Water-adjacent cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `city_salt_ferry_east_hinterland` | hinterland | `(409, 428, 477, 496)` | city_salt_ferry | 400 | 8..16 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `city_salt_ferry_west_hinterland` | hinterland | `(388, 407, 477, 496)` | city_salt_ferry | 384 | 8..15 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `city_salt_road_east_hinterland` | hinterland | `(1024, 1043, 337, 356)` | city_salt_road | 400 | 8..16 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `city_salt_road_west_hinterland` | hinterland | `(997, 1016, 359, 378)` | city_salt_road | 400 | 8..16 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `town_olive_ferry_hinterland` | hinterland | `(704, 723, 232, 251)` | town_olive_ferry | 400 | 8..16 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `southwest_road_03` | corridor (remote) | `(1188, 1207, 416, 435)` | city_salt_road / port_south_tide | 400 | 4..12 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `southwest_road_04` | corridor (remote) | `(549, 568, 337, 356)` | city_salt_ferry / town_olive_ferry | 400 | 4..12 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `southwest_road_05` | corridor (remote) | `(850, 869, 287, 306)` | city_salt_road / port_south_tide | 385 | 4..11 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `southwest_road_06` | corridor (78 cells from 橄欖津) | `(612, 631, 258, 277)` | port_fishers_cove / town_olive_ferry | 400 | 4..12 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `southwest_road_07` | corridor (79 cells from 漁灣鎮) | `(498, 517, 235, 254)` | port_fishers_cove / town_olive_ferry | 400 | 4..12 | 0 | `salt_hauler`, `salt_hauler_pair`, `salt_hauler_column` |
| `salt_road_southeast_wild` | deep | `(1110, 1139, 110, 139)` | remote | 710 | 8..14 | 38 | `reef_burrow_striker`, `seacliff_basker`, `shore_walker`, `oyster_rack_creeper`, `salt_hauler` |
| `salt_road_southwest_wild` | deep | `(930, 959, 120, 149)` | remote | 736 | 8..14 | 36 | `reef_burrow_striker`, `seacliff_basker`, `shore_walker`, `oyster_rack_creeper`, `salt_hauler` |
| `south_tide_east_wild` | deep | `(720, 749, 100, 129)` | remote | 727 | 8..14 | 37 | `reef_burrow_striker`, `seacliff_basker`, `shore_walker`, `oyster_rack_creeper`, `salt_hauler` |
| `southwest_east_cape_wild` | deep | `(1270, 1299, 90, 119)` | remote | 722 | 8..14 | 37 | `reef_burrow_striker`, `seacliff_basker`, `shore_walker`, `oyster_rack_creeper`, `salt_hauler` |
| `white_sail_north_wild` | deep | `(280, 309, 440, 469)` | remote | 855 | 9..17 | 25 | `reef_burrow_striker`, `seacliff_basker`, `shore_walker`, `oyster_rack_creeper`, `salt_hauler` |

Hinterland zones use densities 2..4, corridors 1..3; deep-wild zones are 30×30 with densities 1..2. Every new zone uses cell capacity 3, wave budget 3 and 3600/600 timing. The five edited zones keep their Wave 1 rectangle, densities, capacity and timing.

### D3. Pools, aggression and sites

- New hinterland and corridor pools: `salt_hauler` 1 (solitary, passive), `salt_hauler_pair` 2 (cohesive, passive) and `salt_hauler_column` 3 (cohesive, passive), following the crab's single/pair/trio precedent. The ant forages the dry salt road, olive groves and storehouse ground around the ferry towns; no new hinterland or corridor rectangle holds a water-adjacent cell, so no crab, sea star, shrimp or iguana is pooled there.
- Recorded deviation (remote corridors): the three remote corridors carry no mid-tier composition, because both south-west mid-tier ordinary variants (`reef_burrow_striker`, `seacliff_basker`) are shore animals and every corridor rectangle is dry. `southeast-coast-placement` records the same deviation for the same reason.
- Recorded deviation (corridor count): the region holds about 2,190 road cells (1 km each), so one corridor per 40–60 km would mean about 40 corridors. This change adds five, for seven in total, because the corridor rules (3 cells from the road, at least 45 or 25 cells from any other zone) and the programme's overall zone budget limit the belt. A human reviewer may add corridors later without any test edit.
- Port hinterland additions: `oyster_rack_creeper` 2–3 (cohesive aggregation, passive) and `salt_hauler` 2–3 (cohesive column, passive) beside the three shipped crab compositions; those rectangles already touch the sea under the Wave 1 rule.
- Landed corridor additions (`southwest_road_01`, `southwest_road_02`): `salt_hauler` 2–3 (cohesive, passive).
- Deep-wild pools: `reef_burrow_striker` 1 (solitary, `contact`), `seacliff_basker` 1–2 (cohesive colony, `contact`), and the low company `shore_walker` 1 (solitary, passive), `oyster_rack_creeper` 2–3 and `salt_hauler` 2–3 (cohesive, passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `salt_mound_soldier_mound` | nest | `(850, 320)` | `salt_mound_soldier_mound_group` (`salt_mound_soldier` 1, `salt_hauler` 2) | 3 | recoverable, 86400 | `salt_mound_soldier_mound_crust` |
| `tide_pool_elder_pool` | nest | `(532, 104)` | `tide_pool_elder_pool_group` (`tide_pool_elder` 1, `oyster_rack_creeper` 2) | 3 | recoverable, 86400 | `tide_pool_elder_pool_deep_pool` |
| `seawall_den_holder_den` | nest | `(290, 408)` | `seawall_den_holder_den_member` (`seawall_den_holder` 1) | 1 | recoverable, 86400 | `seawall_den_holder_den_burrow` |
| `salt_dike_holder_dike` | camp | `(468, 98)` | `salt_dike_holder_dike_group` (`salt_dike_holder` 1, `seacliff_basker` 2) | 3 | recoverable, 86400 | `salt_dike_holder_dike_warm_dike` |
| `reef_warden_cove` | nest | `(268, 490)` | `reef_warden_cove_group` (`reef_warden` 1, `shore_walker` 2) | 3 | recoverable, 86400 | `reef_warden_cove_reef` |
| `sunken_anchor_boss_site` | boss_site | `(814, 106)` | `sunken_anchor_boss` (`wreck_den_elder` 1) | 1 | one-shot, individual name 沉錨 | `sunken_anchor_boss_wreck` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. The ant mound sits beside the salt road towards 南潮港, and the boss site lies on the sea cliffs east of 南潮港, matching the species' wreck-and-sea-cave dossier. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Hinterland, corridors, deep wild and sites: south-west coast` after the last existing subsection of that section. Write it without coordinates, densities or counts:

1. One paragraph on the belts: the inland hinterland that Wave 1 deferred, now beside both cities and the olive town, the port hinterlands of Wave 1 with their new company, the added road corridors and the deep-wild zones on the remote shore. State that the deferral recorded under "Near-settlement belts: both coasts" is resolved by the dry-ground ant.
2. One paragraph on species fit: the ant on the dry salt road, olive groves and ferry-town ground, the sea star beside the ports, and the mantis shrimp and the marine iguana with low company on the remote shore, each deep-wild zone touching water.
3. One paragraph on the two recorded deviations: the remote corridors without a mid-tier animal, and a corridor belt sparser than one per 40–60 km of road.
4. One paragraph on sites: the ant's salt-crusted nest mound, the sea star's deep pool, the mantis shrimp's seawall den, the iguana's warm salt-pan dike and the crab's reef of 守礁型 as recoverable sites, and the one-shot octopus boss 沉錨 in a wreck on the sea cliffs east of 南潮港.
5. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [The pool edits touch 5 landed rows] → block 4 lists each full tuple, and task 1.3 checks that each edited row gains exactly the listed number of entries and nothing else.
- [Ant-only hinterlands and corridors repeat one species] → accepted: the ant is the only south-west dry-ground species; the three compositions vary the group size. The human review may add later dry-ground species to these pools without a test edit.
- [Fifteen zones and six sites lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [An open placement change moves a rectangle before this change lands] → the Verification geometry labels fail on any shared cell; move the conflicting rectangle and its grounds together under the D2 rules.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change southwest-coast-placement` and `openspec validate southwest-coast-placement --strict`.
