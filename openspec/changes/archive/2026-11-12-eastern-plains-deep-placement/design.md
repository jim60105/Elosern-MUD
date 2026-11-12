# Design

## Context

See proposal.md (Why). Facts at `d75a2176` plus the planned open placement rows (`north-deep-forest-placement`, `central-mountains-placement`, `northwest-highland-placement`; `highland-road-belts` was open at the probe and has landed since with the same rows) and the planned Wave 2 and Wave 3 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)`, `WeightedComposition(composition_key, weight)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- `eastern-plains-near-belts` (landed, archived) declared 25 `*_hinterland` zones and `eastern_road_01` … `eastern_road_12`, each with one rectangle, grounds `<zone>_grounds` and the same four-entry pool (`grain_pecker`, `burrow_maker`, `mudbank_dweller`, `wax_cache_forager`). Every corridor point is at least 80 cells from every settlement, so all twelve corridors are remote stretches. The new compositions bind activities over those existing grounds.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `d75a2176` (the last commit touching world/lore, the map content and the open placement snippets before this proposal) with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). The landed registries, the rows parsed from the snippet files of the four open placement changes (with `northwest-highland-placement`'s corridor pool edits applied) and this change's rows were loaded together; the not-yet-landed Wave 2 and Wave 3 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The eligible-cell and bound columns below are the probe's `eligible_birth_cells` count and `density_bounds` result. They are planning inputs and are not copied into documentation or tests. The gate at implementation time is the geometry check in the Verification labels, not this probe.
- Water: the published map renders no inland water cell anywhere in the eastern plain. Only `east_pasture_east_wild` touches the sea (10 water-adjacent cells); every other new deep-wild rectangle and all twelve corridors have none. The irrigation canals and fish ponds of the heron dossier are region-wide terrain flavour (`content/maps/continent.yaml`, `terrain_flavor_zh`), so the heron is pooled by the slime precedent recorded under "Content expansion habitats": a bounded rectangle stands in for the canal cells the map does not draw.
- Belt rules the probe applied:
  - Deep-wild rectangle: 30×30, at least 70 cells from every settlement, at least 8 cells from every other zone, area and site grounds, at least 230 cells from every other new deep-wild rectangle (so the five spread across the plain), and at least 880 eligible cells.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region, at an edge distance of at least 2 cells (at least one free cell between) from every zone, area and other grounds, and at least 40 cells from every settlement (80 for the boss site).

## Goals / Non-Goals

**Goals:** the deep-wild belt and the sites of the eastern plains, mid-tier company on the twelve remote corridors, and the new low beetle in the hinterland belt.

**Non-Goals:** new hinterland or corridor zones, edits to the archived `eastern-plains-near-belts` directory, edits to any existing rectangle, density, capacity or timing, edits to the shipped `eastern_field_habitat`, `eastern_mudbank_habitat` and `eastern_cache_habitat` zones, settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- activities of the compositions added to existing zones ---` part, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- compositions added to existing zones ---` part, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.
- Block 4 of the same file is an edit, not an append. For each `# <zone>: the pool becomes` entry, find the existing `EcologyZone` row whose key is `<zone>` and replace its `pool` tuple (the fourth argument, today a four-entry tuple) with the listed tuple. The listed tuple keeps the four existing entries in their order and appends the new ones. It replaces the existing tuple including its closing `),` line, so the row never contains `),,`. Leave every other argument of the row unchanged and append no new row for these keys. The 25 `*_hinterland` entries gain one `WeightedComposition` line each; the 12 `eastern_road_*` entries gain three.

Replace each `# --- ... ---` marker of blocks 1–3 with a one-line comment that names this change and what follows: `# Eastern plains (eastern-plains-deep-placement): ...`. Use "deep-wild zones", "compositions added to the landed hinterland and corridor zones" or "site compositions/extents/activities" as fits. Block 4's comment lines are instructions and are not copied. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor | Eligible birth cells (probe) | Bounds (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- | --- |
| `black_soil_north_wild` | deep | `(1660, 1689, 1605, 1634)` | remote | 900 | 9..18 | `plain_runner`, `sluice_wader`, `road_ball_roller`, `grain_pecker`, `burrow_maker` |
| `crystal_north_wild` | deep | `(2005, 2034, 1890, 1919)` | remote | 892 | 9..17 | `plain_runner`, `sluice_wader`, `road_ball_roller`, `grain_pecker`, `burrow_maker` |
| `east_pasture_east_wild` | deep | `(2500, 2529, 900, 929)` | remote | 892 | 9..17 | `plain_runner`, `sluice_wader`, `road_ball_roller`, `grain_pecker`, `burrow_maker` |
| `north_wood_west_wild` | deep | `(1540, 1569, 1875, 1904)` | remote | 900 | 9..18 | `plain_runner`, `sluice_wader`, `road_ball_roller`, `grain_pecker`, `burrow_maker` |
| `starglow_east_wild` | deep | `(2290, 2319, 1170, 1199)` | remote | 900 | 9..18 | `plain_runner`, `sluice_wader`, `road_ball_roller`, `grain_pecker`, `burrow_maker` |

Every new zone is a 30×30 deep-wild zone with densities 1..2, cell capacity 3, wave budget 3 and 3600/600 timing. The 37 edited zones keep their Wave 1 rectangle, densities 2..4 (hinterland) or 1..3 (corridor), capacity and timing.

### D3. Pools, aggression and sites

- Hinterland addition: `road_ball_roller` 2 (cohesive pair, passive) beside the four shipped low compositions.
- Corridor additions: `road_ball_roller` 2 (cohesive pair, passive), `plain_runner` 1–2 (cohesive herd, `contact`) and `sluice_wader` 1 (solitary, `contact`). Every corridor is a remote stretch, so mid-tier ordinary variants are allowed there; the four shipped low compositions stay as low company.
- Deep-wild pools: `plain_runner` 2–3 (cohesive herd, `contact`), `sluice_wader` 1 (solitary, `contact`), and the low company `road_ball_roller` 2 (cohesive, passive), `grain_pecker` 1–2 (solitary, passive) and `burrow_maker` 1 (solitary, passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `flock_leader_camp` | camp | `(1700, 1100)` | `flock_leader_camp_group` (`flock_leader` 1, `grain_pecker` 2) | 3 | recoverable, 86400 | `flock_leader_camp_stubble` |
| `nest_guard_nest` | nest | `(2200, 1200)` | `nest_guard_nest_group` (`nest_guard` 1, `burrow_maker` 2) | 3 | recoverable, 86400 | `nest_guard_nest_warren` |
| `heap_brood_keeper_heap` | nest | `(2150, 800)` | `heap_brood_keeper_heap_group` (`heap_brood_keeper` 1, `road_ball_roller` 2) | 3 | recoverable, 86400 | `heap_brood_keeper_heap_brood_heap` |
| `herd_stallion_camp` | camp | `(2400, 750)` | `herd_stallion_camp_group` (`herd_stallion` 1, `plain_runner` 2) | 3 | recoverable, 86400 | `herd_stallion_camp_pasture` |
| `heronry_elder_nest` | nest | `(1750, 1700)` | `heronry_elder_nest_group` (`heronry_elder` 1, `sluice_wader` 1) | 2 | recoverable, 86400 | `heronry_elder_nest_heronry` |
| `white_reed_boss_site` | boss_site | `(2150, 1830)` | `white_reed_boss` (`wide_mound_elder` 1) | 1 | one-shot, individual name 白蘆 | `white_reed_boss_reed_bay` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. The boss site lies north-west of 沉鐘鎮, matching the species' lake-district dossier. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Deep wild and sites: eastern plains` after the last existing subsection of that section. Write it without coordinates, densities or counts:

1. One paragraph on the belts: the deep-wild zones spread across the remote plain, and the unchanged hinterland and corridor rectangles of Wave 1.
2. One paragraph on species fit: the dung beetle as passive company beside every farming town and on the official roads, and the wild horse herd and the canal heron as the mid-tier animals of the remote corridors and the deep wild, each with low company. Record the heron's deviation: the map draws no canal or pond cells, so a bounded rectangle stands in for them, as for the slime.
3. One paragraph on the pool edits: the hinterland zones gain the beetle, and the corridors gain the beetle, the horse and the heron, so a traveller on a remote trunk road can meet a mid-tier animal.
4. One paragraph on sites: the sparrow flock camp of 領群型, the hare warren of 護巢型, the beetle brood heap, the stallion's herd pasture and the heronry as recoverable sites, and the one-shot turtle boss 白蘆 in the lake district north-west of 沉鐘鎮.
5. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [The pool edits touch 37 landed rows] → block 4 lists each full tuple, and task 1.3 checks that each edited row gains exactly the listed number of entries and nothing else.
- [Five deep-wild zones and six sites lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [The heron appears in rectangles with no drawn water] → recorded as the slime-precedent deviation in Context and in D4 item 2; the human review may drop `sluice_wader` from a pool that reads dry without any test edit.
- [An open placement change moves a rectangle before this change lands] → the Verification geometry labels fail on any shared cell; move the conflicting rectangle and its grounds together under the D2 rules.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change eastern-plains-deep-placement` and `openspec validate eastern-plains-deep-placement --strict`.
