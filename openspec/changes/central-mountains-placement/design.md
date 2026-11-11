# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 placement rows and the planned Wave 1 and Wave 2 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `d1ac4b84` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). With the 9 shipped zones, every Wave 1 zone and site, and this change's rows loaded together, `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The Wave 1 and Wave 2 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. The eligible-cell column below is the probe's `eligible_birth_cells` count. It is a planning input and is not copied into documentation or tests. Since the probe, `eastern-plains-near-belts`, `western-hills-near-belts` and `coastal-near-belts` have landed on master with the rectangles the probe already included, so it was not re-run. The gate at implementation time is the geometry check in the Verification labels, not this probe.
- Belt rules the probe applied:
  - Hinterland rectangle: 20×20, nearest edge 3–8 cells (Chebyshev) from the settlement footprint, at least 4 cells from every other settlement footprint, at least 2 cells from every other zone, activity area and site grounds, and at least 340 of its 400 cells valid cells of the settlement's region. Elven villages get one rectangle each.
  - Approach rectangle (stands in for the road-corridor belt, because no road enters the region): 20×20, on the mountain side of a foothill settlement, at least 30 cells from every settlement and at least 380 valid region cells.
  - Deep-wild rectangle: 30×30 on the spine, at least 60 cells from every settlement and at least 5 cells from every other zone, area and site grounds.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region, at least 2 cells clear of every zone, area and other grounds, and at least 40 cells from every settlement.

## Goals / Non-Goals

**Goals:** hinterland zones beside both elven villages, the mountain-path approach belt, the deep-wild belt and sites for the central mountains.

**Non-Goals:** roads or passes, settlement birth policies, quest content, edits to species rows, edits to Wave 1 zones, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.

Replace each `# --- ... ---` marker with a one-line comment that names this change and what follows: `# Central mountains (central-mountains-placement): ...`. Use "hinterland, approach and deep-wild zones" or "site compositions/extents/activities" as fits. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `village_ciaran_hinterland` | hinterland | `(1370, 1389, 538, 557)` | village_ciaran | 400 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `village_fionnen_hinterland` | hinterland | `(1469, 1488, 1221, 1240)` | village_fionnen | 400 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `fox_fire_pass_approach` | approach | `(1329, 1348, 1690, 1709)` | city_fox_fire | 400 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `maple_foot_pass_approach` | approach | `(1502, 1521, 1246, 1265)` | town_maple_foot | 381 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `scarp_pass_approach` | approach | `(1309, 1328, 672, 691)` | town_scarp | 382 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `silver_ridge_pass_approach` | approach | `(1471, 1490, 751, 770)` | town_silver_ridge | 400 | `seep_sipper`, `seep_sipper_single`, `ledge_basker` |
| `ciaran_ridge_wild` | deep | `(1351, 1380, 235, 264)` | remote | 900 | `updraft_glider`, `lamp_seeker`, `seep_sipper`, `ledge_basker` |
| `fionnen_ridge_wild` | deep | `(1365, 1394, 1005, 1034)` | remote | 900 | `updraft_glider`, `lamp_seeker`, `seep_sipper`, `ledge_basker` |
| `fox_fire_high_wild` | deep | `(1360, 1389, 1545, 1574)` | remote | 900 | `updraft_glider`, `lamp_seeker`, `seep_sipper`, `ledge_basker` |
| `north_spine_wild` | deep | `(1361, 1390, 1805, 1834)` | remote | 900 | `updraft_glider`, `lamp_seeker`, `seep_sipper`, `ledge_basker` |
| `silver_ridge_high_wild` | deep | `(1362, 1391, 745, 774)` | remote | 900 | `updraft_glider`, `lamp_seeker`, `seep_sipper`, `ledge_basker` |

Belts: the two `*_hinterland` zones are the hinterland belt (densities 2..4). The four `*_pass_approach` zones are approach zones where foothill traffic climbs in (densities 1..3), standing in for the road-corridor belt. The five `*_wild` zones are 30×30 deep-wild zones (densities 1..2). Every zone uses cell capacity 3, wave budget 3 and 3600/600 timing.

### D3. Pools, aggression and sites

- Hinterland and approach pools: `seep_sipper` 2–3 (cohesive colony, passive), `seep_sipper` 1 (suffix `seep_sipper_single`, solitary, passive) and `ledge_basker` 1 (solitary, passive).
- Deep-wild pools: `updraft_glider` 1 (solitary, `contact`), `lamp_seeker` 1 (solitary, `contact` at `dusk` and `midnight` only, because the moth flies at night), and the low company `seep_sipper` 2–3 and `ledge_basker` 1 (passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `spring_keeper_pool` | nest | `(1420, 420)` | `spring_keeper_pool_group` (`spring_keeper` 1, `seep_sipper` 2) | 3 | recoverable, 86400 | `spring_keeper_pool_pool` |
| `vent_crack_den` | nest | `(1420, 1300)` | `vent_crack_den_member` (`vent_crack_dweller` 1) | 1 | recoverable, 86400 | `vent_crack_den_crack` |
| `crag_nest_ledge` | nest | `(1396, 604)` | `crag_nest_ledge_member` (`crag_nest_vulture` 1) | 1 | recoverable, 86400 | `crag_nest_ledge_ledge` |
| `old_veil_lamp_camp` | camp | `(1430, 900)` | `old_veil_lamp_camp_member` (`old_veil_moth` 1) | 1 | recoverable, 86400 | `old_veil_lamp_camp_lamp` |
| `rime_coil_boss_site` | boss_site | `(1406, 96)` | `rime_coil_boss` (`white_rime_coil` 1) | 1 | one-shot, individual name 霜環 | `rime_coil_boss_ravine` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Near-settlement belts: central mountains` after the last existing subsection. Write it without coordinates, densities or counts:

1. One paragraph on the belts: hinterland beside 暗影谷村 and 翠綠森林村, approach zones on the mountain side of 斷崖鎮, 銀嶺鎮, 楓麓鎮 and 狐火城 where foothill traffic climbs in, and deep-wild zones along the spine. It also notes that no road enters the region, so the approach belt replaces the corridor belt.
2. One paragraph on species fit: frog colonies at seeps and salamanders on sunlit scree beside the villages and paths, and the vulture and the moth with low company on the high spine.
3. One paragraph on sites: the stronger variants' spring pool, warm vent crack, nest ledge and guide-lamp camp, and the one-shot serpent boss 霜環 in a remote ravine at the southern end of the spine.
4. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [Hinterland zones beside the hidden elven villages could read as exposing them] → the zones hold only low-tier passive animals, and nothing in the published data names a village beyond its existing anchor. The human review may move a rectangle to another side without any test edit.
- [Moth contact only at dusk and midnight] → this is a closed-vocabulary daypart condition already supported by `AggressionCondition`.
- [More individuals lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change central-mountains-placement` and `openspec validate central-mountains-placement --strict`.
