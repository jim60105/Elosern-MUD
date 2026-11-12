# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned open placement rows (`north-deep-forest-placement`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement`, `southeast-coast-placement`, `southwest-coast-placement`) and the planned Wave 2, Wave 3 and Wave 4 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)`, `WeightedComposition(composition_key, weight)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- `western-hills-near-belts` (landed, archived) declared 19 `*_hinterland` zones, each with the four-entry low pool (`burrow_maker`, `mudbank_dweller`, `wax_cache_forager`, `hanging_nest_forager`), the remote corridors `western_road_01`, `western_road_02` and `western_road_04` … `western_road_10`, each with the three-entry pool (`cliff_stepper`, `burrow_maker`, `hanging_nest_forager`), and `western_road_03` with the four-entry low pool. Each has one rectangle and grounds `<zone>_grounds`. The new compositions bind activities over those existing grounds.
- The shipped sites `ridge_burrow_nest`, `cliff_echo_camp`, `abandoned_transfer_station_encounter` and `ember_bristle_boss_site` and the four earlier `western_*_habitat` zones stay as they are.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `cf4643a1` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). The landed registries, the rows parsed from the snippet files of the six open placement changes (with their pool edits applied) and this change's rows were loaded together; the not-yet-landed Wave 2, Wave 3 and Wave 4 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The eligible-cell and bound columns below are probe outputs. They are planning inputs and are not copied into documentation or tests. The gate at implementation time is the geometry check in the Verification labels, not this probe.
- Belt rules the probe applied:
  - Deep-wild rectangle: 30×30, at least 70 cells from every settlement, at least 8 cells from every other zone, area and site grounds, at least 120 cells from every other new deep-wild rectangle and at least 850 eligible cells. No water rule applies: every pooled species is a dry-ground animal. Five rectangles qualify at the 120-cell spacing other regions used.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region, at an edge distance of at least 2 cells (at least one free cell between) from every zone, area and other grounds, and at least 40 cells from every settlement.

## Goals / Non-Goals

**Goals:** the deep-wild belt of the western hills, the new low species beside every settlement and on every corridor, the new mid species on the remote corridors, and the sites of the new and shipped stronger variants.

**Non-Goals:** new corridor zones, edits to the archived `western-hills-near-belts` directory, edits to any existing rectangle, density, capacity or timing, edits to the four shipped western sites or the four `western_*_habitat` zones, settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- activities of the compositions added to existing zones ---` part, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- compositions added to existing zones ---` part, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.
- Block 4 of the same file is an edit, not an append. For each `# <zone>: the pool becomes` entry, find the existing `EcologyZone` row whose key is `<zone>` and replace its `pool` tuple (the fourth argument, today a three- or four-entry tuple) with the listed tuple. The listed tuple keeps the existing entries in their order and appends the new ones. It replaces the existing tuple including its closing `),` line, so the row never contains `),,`. Leave every other argument of the row unchanged and append no new row for these keys. The 19 hinterland entries and `western_road_03` gain one `WeightedComposition` line each; the nine remote corridor entries gain two each.

Replace each `# --- ... ---` marker of blocks 1–3 with a one-line comment that names this change and what follows: `# Western hills (western-hills-deep-placement): ...`. Use "deep-wild zones", "compositions added to the landed hinterland and corridor zones" or "site compositions/extents/activities" as fits. Block 4's comment lines are instructions and are not copied. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor | Eligible birth cells (probe) | Bounds (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- | --- |
| `capital_south_wild` | deep | `(810, 839, 810, 839)` | remote | 900 | 9..18 | `quarry_pit_lurker`, `cliff_stepper`, `cellar_leaper`, `burrow_maker`, `hanging_nest_forager` |
| `confluence_southeast_wild` | deep | `(730, 759, 520, 549)` | remote | 900 | 9..18 | `quarry_pit_lurker`, `cliff_stepper`, `cellar_leaper`, `burrow_maker`, `hanging_nest_forager` |
| `east_river_east_wild` | deep | `(1270, 1299, 940, 969)` | remote | 900 | 9..18 | `quarry_pit_lurker`, `cliff_stepper`, `cellar_leaper`, `burrow_maker`, `hanging_nest_forager` |
| `east_river_northeast_wild` | deep | `(1240, 1269, 1140, 1169)` | remote | 900 | 9..18 | `quarry_pit_lurker`, `cliff_stepper`, `cellar_leaper`, `burrow_maker`, `hanging_nest_forager` |
| `greyrock_northwest_wild` | deep | `(170, 199, 1250, 1279)` | remote | 900 | 9..18 | `quarry_pit_lurker`, `cliff_stepper`, `cellar_leaper`, `burrow_maker`, `hanging_nest_forager` |

Deep-wild zones are 30×30 with densities 1..2, cell capacity 3, wave budget 3 and 3600/600 timing. The 29 edited zones keep their Wave 1 rectangle, densities, capacity and timing.

### D3. Pools, aggression and sites

- Hinterland additions: `cellar_leaper` 2–3 (cohesive swarm, passive) beside the four shipped low compositions; the cricket lives in the cellars, storerooms and mine mouths at the edge of every hill town.
- Remote corridor additions (`western_road_01`, `western_road_02`, `western_road_04` … `western_road_10`): `quarry_pit_lurker` 1 (solitary, `contact`) and `cellar_leaper` 2–3 (cohesive, passive) beside the shipped goat, hare and goblin compositions. The antlion digs its pits in the sandy verges and spoil beside the hill transport routes.
- `western_road_03` addition: `cellar_leaper` 2–3 (cohesive, passive); this corridor stays low tier, as Wave 1 left it.
- Deep-wild pools: `quarry_pit_lurker` 1 (solitary, `contact`), the shipped `cliff_stepper` 1 (solitary, passive, the shipped corridor binding), and the low company `cellar_leaper` 2–3 and `hanging_nest_forager` 2–3 (cohesive, passive) and `burrow_maker` 1 (solitary, passive).
- Recorded deviation (corridor count): the region holds about 4,140 road cells (1 km each), so one corridor per 40–60 km would mean about 70 to 100 corridors. This change adds none and keeps the ten landed corridors, because the brief for this wave asks only for mid compositions on the remote corridors where they fit, and the programme's overall zone budget is reached with the deep-wild belts. A human reviewer may add corridors later without any test edit.
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `old_shaft_leaper_shaft` | camp | `(390, 930)` | `old_shaft_leaper_shaft_group` (`old_shaft_leaper` 1, `cellar_leaper` 2) | 3 | recoverable, 86400 | `old_shaft_leaper_shaft_shaft_mouth` |
| `spoil_heap_elder_pit` | nest | `(270, 1080)` | `spoil_heap_elder_pit_member` (`spoil_heap_elder` 1) | 1 | recoverable, 86400 | `spoil_heap_elder_pit_funnel` |
| `pass_warden_ledge` | camp | `(1150, 1230)` | `pass_warden_ledge_group` (`pass_warden` 1, `cliff_stepper` 1) | 2 | recoverable, 86400 | `pass_warden_ledge_ledge` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. The shaft camp and the spoil-heap pit lie in the mining ground around 灰岩城, and the goat ledge lies on remote hills in the region's east. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Deep wild, corridor company and sites: western hills and valleys` after the last existing subsection of that section. Write it without coordinates, densities or counts:

1. One paragraph on the belts: the Wave 1 hinterlands and corridors with their new company, and the deep-wild zones on remote hill ground.
2. One paragraph on species fit: the cave cricket beside every town, where cellars, storerooms and mine mouths edge the settlements, the antlion beside the goat on the remote hill roads, and both with the shipped low animals in the deep wild.
3. One paragraph on the recorded deviation: no new corridor, and why the corridor belt stays as Wave 1 left it.
4. One paragraph on sites: the cricket swarm at an abandoned shaft mouth, the antlion's spoil-heap pit, and the goat ledge of 守隘型 as recoverable sites, with the shipped hare nest, goat camp, transfer station and boar boss site left unchanged.
5. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [The pool edits touch 29 landed rows] → block 4 lists each full tuple, and task 1.3 checks that each edited row gains exactly the listed number of entries and nothing else.
- [A mid-tier antlion on the remote corridors] → the corridor rectangles lie at least 30 cells from every settlement, and Wave 1 already pools the mid-tier goat there; the ground beside the towns stays low tier.
- [Five zones and three sites lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [An open placement change moves a rectangle before this change lands] → the Verification geometry labels fail on any shared cell; move the conflicting rectangle and its grounds together under the D2 rules.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change western-hills-deep-placement` and `openspec validate western-hills-deep-placement --strict`.
