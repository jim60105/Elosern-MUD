# Design

## Context

See proposal.md (Why). Facts at `253c7147` plus the planned open placement rows (`north-deep-forest-placement`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement`) and the planned Wave 2 and Wave 3 species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)`, `WeightedComposition(composition_key, weight)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- `coastal-near-belts` (landed, archived) declared `port_east_bay_hinterland`, `port_golden_sheaf_hinterland` and `port_south_cape_hinterland` with the three-entry crab pool (`shore_walker`, `shore_walker_pair`, `shore_walker_trio`), and `southeast_road_01` with `bank_lurker`, `shore_walker` and `shore_walker_pair`, each with one rectangle and grounds `<zone>_grounds`. The new compositions bind activities over those existing grounds.
- The south-east trunk road is one route: the roads `city_twin_currents`–`port_golden_sheaf` and `port_east_bay`–`port_golden_sheaf` share the stretch inside this region, which runs north from 金穗港 to the region boundary. The `port_east_bay` end of the second road leaves the region within 31 cells of 東灣港, beside that port's hinterland zone.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- Planning probe, run while writing this proposal against `253c7147` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). The landed registries, the rows parsed from the snippet files of the four open placement changes (with their pool edits applied) and this change's rows were loaded together; the not-yet-landed Wave 2 and Wave 3 variant keys were validated with stand-in variant and species faces whose `habitat_tags` match their species changes. `validate_ecology_geometry(...)` returned `()`, `activity_area_problems` reported nothing for any new grounds, and import-time validation accepted every row. The eligible-cell, bound and water-adjacent columns below are probe outputs (a water-adjacent cell is a valid region cell with a non-land cell among its 8 neighbours). They are planning inputs and are not copied into documentation or tests. The gate at implementation time is the geometry check in the Verification labels, not this probe.
- Belt rules the probe applied:
  - Corridor rectangle: 20×20, 3 cells from a road cell of `world/maps/data/road_network.json`, at least 30 cells from any settlement, and at least 45 cells (the remote corridor) or 15 cells (the corridor near 金穗港) from any other zone. A corridor point at least 80 cells from every settlement counts as remote.
  - Deep-wild rectangle: 30×30, at least 70 cells from every settlement, at least 8 cells from every other zone, area and site grounds, at least 60 cells from every other new deep-wild rectangle, at least 12 water-adjacent cells (the shore-dossier rule Wave 1 applied to the crab) and at least 600 eligible cells.
  - Site: a valid wilderness cell whose 21×21 grounds lie wholly inside the region and hold at least 10 water-adjacent cells, at an edge distance of at least 2 cells (at least one free cell between) from every zone, area and other grounds, and at least 40 cells from every settlement.
- Deep-wild count: the region's remote ground holds five such rectangles only with the 60-cell spacing above; at the 120-cell spacing other regions used, two qualify. Five fully dry 30×30 rectangles also fit at 120-cell spacing, but they hold no water-adjacent cell, so a shore pool there would contradict every south-east dossier. This change places the five water-adjacent rectangles.

## Goals / Non-Goals

**Goals:** the new low species beside the ports, two more trunk-road corridors, the deep-wild belt and the sites of the south-east coast.

**Non-Goals:** hinterland zones for the deferred south-west settlements, edits to the archived `coastal-near-belts` directory, edits to any existing rectangle, density, capacity or timing, edits to the two shipped crocodile boss sites (`tide_mouth_boss_site`, `reservoir_crocodile_boss_site`), settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- activities of the compositions added to existing zones ---` part, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- compositions added to existing zones ---` part, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.
- Block 4 of the same file is an edit, not an append. For each `# <zone>: the pool becomes` entry, find the existing `EcologyZone` row whose key is `<zone>` and replace its `pool` tuple (the fourth argument, today a three-entry tuple) with the listed tuple. The listed tuple keeps the three existing entries in their order and appends the new ones. It replaces the existing tuple including its closing `),` line, so the row never contains `),,`. Leave every other argument of the row unchanged and append no new row for these keys. The three `port_*_hinterland` entries gain two `WeightedComposition` lines each; `southeast_road_01` gains one.

Replace each `# --- ... ---` marker of blocks 1–3 with a one-line comment that names this change and what follows: `# South-east coast (southeast-coast-placement): ...`. Use "road-corridor and deep-wild zones", "compositions added to the landed port hinterland and corridor zones" or "site compositions/extents/activities" as fits. Block 4's comment lines are instructions and are not copied. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor | Eligible birth cells (probe) | Bounds (probe) | Water-adjacent cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `southeast_road_02` | corridor (remote) | `(2060, 2079, 477, 496)` | city_twin_currents / port_golden_sheaf | 380 | 4..11 | 0 | `mast_circler`, `mast_circler_pair`, `mast_circler_flock` |
| `southeast_road_03` | corridor (66 cells from 金穗港) | `(2059, 2078, 307, 326)` | city_twin_currents / port_golden_sheaf | 380 | 4..11 | 0 | `mast_circler`, `mast_circler_pair`, `mast_circler_flock` |
| `east_bay_west_wild` | deep | `(2220, 2249, 380, 409)` | remote | 855 | 9..17 | 25 | `pier_basker`, `bank_lurker`, `shore_walker`, `mudflat_skipper`, `mast_circler` |
| `golden_sheaf_northeast_wild` | deep | `(2130, 2159, 330, 359)` | remote | 824 | 9..16 | 26 | `pier_basker`, `bank_lurker`, `shore_walker`, `mudflat_skipper`, `mast_circler` |
| `golden_sheaf_southwest_wild` | deep | `(1870, 1899, 120, 149)` | remote | 821 | 9..16 | 35 | `pier_basker`, `bank_lurker`, `shore_walker`, `mudflat_skipper`, `mast_circler` |
| `golden_sheaf_west_wild` | deep | `(1960, 1989, 150, 179)` | remote | 886 | 9..17 | 13 | `pier_basker`, `bank_lurker`, `shore_walker`, `mudflat_skipper`, `mast_circler` |
| `south_cape_east_wild` | deep | `(1780, 1809, 80, 109)` | remote | 768 | 8..15 | 38 | `pier_basker`, `bank_lurker`, `shore_walker`, `mudflat_skipper`, `mast_circler` |

Corridors use densities 1..3; deep-wild zones are 30×30 with densities 1..2. Every new zone uses cell capacity 3, wave budget 3 and 3600/600 timing. The four edited zones keep their Wave 1 rectangle, densities, capacity and timing.

### D3. Pools, aggression and sites

- Port hinterland additions: `mudflat_skipper` 2–3 (cohesive colony, passive) and `mast_circler` 2–3 (cohesive flock, passive) beside the three shipped crab compositions.
- `southeast_road_01` addition: `mast_circler` 2–3 (cohesive flock, passive) beside the shipped crocodile and crab compositions.
- New corridors: `mast_circler` 1 (solitary, passive), `mast_circler_pair` 2 (cohesive, passive) and `mast_circler_flock` 3 (cohesive, passive), following the crab's single/pair/trio precedent. Gulls follow the fish and grain carts on the trunk road; the road rectangles hold no water, so no crab, mudskipper, seal or crocodile is pooled there, and the remote corridor carries no mid-tier composition for the same reason. This is a recorded deviation from the corridor rule that remote stretches hold mid-tier ordinary variants: every south-east mid-tier ordinary variant (`pier_basker`, `bank_lurker`) is a shore animal.
- Deep-wild pools: `pier_basker` 1–2 (cohesive colony, `contact`), `bank_lurker` 1 (solitary, `contact`, the shipped crocodile binding), and the low company `shore_walker` 1 (solitary, passive), `mudflat_skipper` 2–3 and `mast_circler` 2–3 (cohesive, passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `reef_warden_reef` | nest | `(1822, 98)` | `reef_warden_reef_group` (`reef_warden` 1, `shore_walker` 2) | 3 | recoverable, 86400 | `reef_warden_reef_reef` |
| `bay_warden_bay` | nest | `(2262, 404)` | `bay_warden_bay_member` (`bay_warden` 1) | 1 | recoverable, 86400 | `bay_warden_bay_backwater` |
| `turret_keeper_flat` | nest | `(2122, 302)` | `turret_keeper_flat_group` (`turret_keeper` 1, `mudflat_skipper` 2) | 3 | recoverable, 86400 | `turret_keeper_flat_turrets` |
| `stack_colony_elder_rocks` | camp | `(1962, 138)` | `stack_colony_elder_rocks_group` (`stack_colony_elder` 1, `mast_circler` 2) | 3 | recoverable, 86400 | `stack_colony_elder_rocks_colony` |
| `haulout_bull_sandbar` | camp | `(2284, 406)` | `haulout_bull_sandbar_group` (`haulout_bull` 1, `pier_basker` 1) | 2 | recoverable, 86400 | `haulout_bull_sandbar_haulout` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Deep wild, corridors and sites: south-east coast` after the last existing subsection of that section. Write it without coordinates, densities or counts:

1. One paragraph on the belts: the port hinterlands of Wave 1 with their new company, the two added trunk-road corridors, and the deep-wild zones on the remote shore. State that every south-east settlement is a port with its Wave 1 hinterland zone, so no deferred hinterland applies here, and that the deferred inland coastal settlements belong to the south-west coast.
2. One paragraph on species fit: the mudskipper and the harbour gull beside the ports, the gull alone on the dry trunk road where it follows the fish and grain carts, and the harbour seal and the crocodile with low company on the remote shore, each deep-wild zone touching water.
3. One paragraph on the deep-wild count: five water-adjacent rectangles fit only at a closer spacing than other regions used; dry rectangles were set aside because they would hold shore animals away from the shore.
4. One paragraph on sites: the crab's reef of 守礁型, the crocodile's backwater of 守灣型, the mudskipper's turret flat, the gull colony rocks and the seal's sandbar as recoverable sites, and the two shipped crocodile boss sites left unchanged.
5. A verification table listing the commands of the Verification section and their observed results, plus the before and after duration of `world.maps.tests.test_bootstrap.test_bootstrap_grid.WildernessBootstrapTests` as a non-gating observation.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [The pool edits touch 4 landed rows] → block 4 lists each full tuple, and task 1.3 checks that each edited row gains exactly the listed number of entries and nothing else.
- [The closer deep-wild spacing groups the zones along one shore] → accepted for species fit (D3, D4 item 3). The human review may drop a deep-wild zone without any test edit.
- [Seven zones and five sites lengthen fresh provisioning] → record the bootstrap duration in the D4 table as a non-gating observation. Nothing gates on it.
- [An open placement change moves a rectangle before this change lands] → the Verification geometry labels fail on any shared cell; move the conflicting rectangle and its grounds together under the D2 rules.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.maps.tests.test_regional_population`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change southeast-coast-placement` and `openspec validate southeast-coast-placement --strict`.
