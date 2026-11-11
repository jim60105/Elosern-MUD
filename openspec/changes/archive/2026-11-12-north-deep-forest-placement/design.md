# Design

## Context

See proposal.md (Why). Facts at `9b67edf2` plus the planned species rows:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`, `EncounterComposition(key, activity_key, members)` and `CompositionMember(variant_key, minimum, maximum)` live in `world/lore/monster_placement.py`. `ActivityArea(key, region_key, rectangles)`, `MonsterActivity(key, policy, area_key, decision_interval, aggression)` and `AggressionCondition(kind, area_key=None, dayparts=())` live in `world/lore/monster_activity.py`.
- Import-time validation (`validate_ecology_registries`, `validate_activity_registries`) checks references, habitat tags, integer ranges and that each composition's largest total fits `cell_capacity` and `wave_budget`. Candidate publication (`world/maps/population_geometry.py::validate_ecology_geometry`, run from `world/maps/geography.py`) checks region intersection, map validity, settlement exclusion, the density interval, recoverability, and that no two zones share a parent-region cell.
- Every zone's grounds repeat its birth rectangle (`docs/development/regional-monster-population.md`, "Content expansion habitats"). No validator ties the two together, so the snippets write both.
- Fresh wilderness provisioning (`world/maps/bootstrap.py::_provision_wilderness_script`) initializes every shipped zone once. An existing development world refuses at startup with `population_state_uninitialized`, naming the new zones. Pre-release, the supported recovery is the reset in `docs/development/database-reset.md`. No migration is added.
- `population-zone-pass-indexing` (merged at `3756992d`) makes one boundary zone pass read the state record once and scan presence once, so the boundary cost of the larger zone set grows linearly.
- Planning probe, run while writing this proposal against `9b67edf2` with the published map world (the `tools.map_reference_context` bootstrap and `world.maps.geography.current()`). Neither world/lore nor the map content has changed since. With every Wave 1 zone loaded together (the 9 shipped zones plus this change's rectangles and the rectangles of the sibling placement changes), `validate_ecology_geometry(...)` returned `()` and `activity_area_problems` reported nothing for any new grounds. Import-time validation also accepted every row. The eligible-cell column below is the probe's `eligible_birth_cells` count. It is a planning input and is not copied into documentation or tests.
- Belt rules the probe applied:
  - Hinterland rectangle: 20×20, nearest edge 3–8 cells (Chebyshev) from the settlement footprint, at least 4 cells from every other settlement footprint, at least 2 cells from every other zone, activity area and site grounds, and at least 340 of its 400 cells valid cells of the settlement's region. Capitals and cities get two rectangles on different sides.
  - Corridor rectangle: 20×20, 3 cells from a road cell of `world/maps/data/road_network.json`, at least 30 cells from any settlement and at least 45 cells from any other zone. Sides alternate within a region, and a corridor point at least 80 cells from every settlement counts as remote.
- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_name_zh=None)`. `validate_monster_placement_registry` checks kind, region, cell shape, capacity against the composition's largest total, the one-shot/recovery rule and that an individual name sits on a composition whose every legal outcome is exactly one.
- The north-deep-forest variant keys come from the six species changes. The probe validated them with stand-in variant and species faces whose `habitat_tags` are `("north_deep_forest",)`, as those changes declare.
- Region facts from the probe: the deep-forest edge lies about 65 cells north of 北林堡 and about 80 cells north of 虎嘯城, and no forest cell lies within 8 cells of either town. The dungeon anchors are `dungeon_dragon_nest` `(1815, 2149)` and `dungeon_eternal_night` `(900, 2350)`, and `village_eolas` is at `(1410, 2150)`. Every site cell is a valid wilderness cell of `north_deep_forest`, and every site's 21×21 grounds lie wholly inside the region, clear of every zone rectangle.

## Goals / Non-Goals

**Goals:** a hinterland zone, the expedition-entry approach belt, the deep-wild belt and sites for the north deep forest.

**Non-Goals:** road corridors (the region forbids roads), settlement birth policies, quest content, edits to species rows, and any mechanism change.

## Decisions

### D1. Declarations (verbatim transcription)

- Block 1 of `snippets/monster_activity_rows.txt` (zone grounds, then the `# --- site extents ---` part) goes at the end of `_ACTIVITY_AREA_DECLARATIONS`.
- Block 2 of the same file (zone activities, then the `# --- site activities ---` part) goes at the end of `_ACTIVITY_DECLARATIONS`.
- Block 1 of `snippets/monster_placement_rows.txt` (zone compositions, then the `# --- site compositions ---` part) goes at the end of `_ENCOUNTER_COMPOSITION_DECLARATIONS`.
- Block 2 of the same file (`EcologyZone` rows) goes at the end of `_ECOLOGY_ZONE_DECLARATIONS`.
- Block 3 of the same file (`MonsterSite` rows) goes at the end of `_SITE_DECLARATIONS`.

Replace each `# --- ... ---` marker with a one-line comment that names this change and what follows: `# North deep forest (north-deep-forest-placement): ...`. Use "hinterland, approach and deep-wild zones" or "site compositions/extents/activities" as fits. Keep every row unchanged.

### D2. Zones

| Zone key | Belt | Rectangle `(x0, x1, y0, y1)` | Anchor settlement / road | Eligible birth cells (probe) | Pool composition suffixes |
| --- | --- | --- | --- | --- | --- |
| `village_eolas_hinterland` | hinterland | `(1414, 1433, 2134, 2153)` | village_eolas | 400 | `rotlog_sprout`, `quill_forager`, `hollow_roost_flier` |
| `north_wood_forest_edge` | approach | `(1805, 1824, 1950, 1969)` | forest edge | 400 | `rotlog_sprout`, `quill_forager`, `hollow_roost_flier` |
| `tiger_roar_forest_edge` | approach | `(990, 1009, 1950, 1969)` | forest edge | 400 | `rotlog_sprout`, `quill_forager`, `hollow_roost_flier` |
| `dragon_nest_lower_wild` | deep | `(1830, 1859, 2010, 2039)` | expedition approach | 900 | `hush_wing_hunter`, `vine_weaver`, `quill_forager`, `hollow_roost_flier` |
| `dragon_nest_upper_wild` | deep | `(1770, 1799, 2085, 2114)` | expedition approach | 900 | `hush_wing_hunter`, `vine_weaver`, `quill_forager`, `hollow_roost_flier` |
| `eternal_night_lower_wild` | deep | `(965, 994, 2020, 2049)` | expedition approach | 900 | `hush_wing_hunter`, `vine_weaver`, `quill_forager`, `hollow_roost_flier` |
| `eternal_night_upper_wild` | deep | `(915, 944, 2200, 2229)` | expedition approach | 900 | `hush_wing_hunter`, `vine_weaver`, `quill_forager`, `hollow_roost_flier` |
| `moonvale_outer_wild` | deep | `(1590, 1619, 2140, 2169)` | expedition approach | 900 | `hush_wing_hunter`, `vine_weaver`, `quill_forager`, `hollow_roost_flier` |

Belts: `village_eolas_hinterland` is the hinterland belt (densities 2..4). The two `*_forest_edge` zones are approach zones at the expedition entry points (densities 1..3), standing in for the road-corridor belt. The five `*_wild` zones are 30×30 deep-wild zones (densities 1..2). Every zone uses cell capacity 3, wave budget 3 and 3600/600 timing.

### D3. Pools, aggression and sites

- Hinterland and approach pools: `rotlog_sprout` 2–3 (cohesive colony, passive), `quill_forager` 1 (solitary, passive) and `hollow_roost_flier` 2–3 (cohesive colony, passive).
- Deep-wild pools: `hush_wing_hunter` 1 (solitary, `contact` at `dusk` and `midnight` only, because the owl hunts then), `vine_weaver` 1 (solitary, `contact`), and the low company `quill_forager` 1 and `hollow_roost_flier` 2–3 (passive).
- Sites:

| Site key | Kind | Cell | Composition (members) | Capacity | Life cycle | Defended extent |
| --- | --- | --- | --- | --- | --- | --- |
| `fairy_ring_nest` | nest | `(1700, 2000)` | `fairy_ring_nest_group` (`ring_elder` 1, `rotlog_sprout` 2) | 3 | recoverable, 86400 | `fairy_ring_nest_ring` |
| `quill_den_nest` | nest | `(1080, 1990)` | `quill_den_nest_group` (`den_sentry` 1, `quill_forager` 1) | 2 | recoverable, 86400 | `quill_den_nest_den` |
| `hollow_roost_camp` | camp | `(880, 2300)` | `hollow_roost_camp_group` (`colony_sentinel` 1, `hollow_roost_flier` 2) | 3 | recoverable, 86400 | `hollow_roost_camp_roost` |
| `old_hollow_owl_nest` | nest | `(1250, 2100)` | `old_hollow_owl_nest_member` (`old_hollow_owl` 1) | 1 | recoverable, 86400 | `old_hollow_owl_nest_hollow` |
| `trail_net_camp` | camp | `(1840, 2120)` | `trail_net_camp_member` (`trail_netter` 1) | 1 | recoverable, 86400 | `trail_net_camp_web` |
| `moss_crown_boss_site` | boss_site | `(1300, 2400)` | `moss_crown_boss` (`wood_crown_elder` 1) | 1 | one-shot, individual name 蒼冠 | `moss_crown_boss_glade` |

  Every site declares no activity override. Its composition binds one activity over its 21×21 grounds, with a `defended_area` condition on the 11×11 extent centred on the site cell. Recoverable sites re-form one in-game day after clearing. No stronger or high-tier variant joins any ordinary pool.

### D4. Human-review documentation

Under `## Authoring review (human judgment)` in `docs/development/regional-monster-population.md`, add `### Near-settlement belts: north deep forest` after the last existing subsection. Write it without coordinates, densities or counts:

1. One paragraph on the belts: hinterland beside 幽月谷村, forest-edge approach zones where the 北林堡 and 虎嘯城 expeditions enter, and deep-wild zones on the approaches to the dragon nest and the eternal-night dungeon. It also notes that the region has no roads, so the approach belt replaces the corridor belt.
2. One paragraph on species fit: mushroom colonies and porcupines on fallen logs and forest edges, bats along the dungeon approaches, and the owl and spider in the deep wild.
3. One paragraph on sites: the stronger variants' nests and camps (菌環, 守洞 den, roost, old owl hollow, path-blocking net) and the one-shot stag boss 蒼冠 in a remote clearing.
4. A verification table listing the commands of the Verification section and their observed results.

### D5. Reference context

Run `uv run --locked python -m tools.map_reference_context`, then `--check`.

## Risks / Trade-offs

- [A hinterland zone beside the hidden elven village could read as exposing it] → the zone holds only low-tier passive animals, and nothing in the published data names the village beyond its existing anchor. The human review may move the rectangle to another side without any test edit.
- [Owl contact only at dusk and midnight] → this is a closed-vocabulary daypart condition already supported by `AggressionCondition`.
- [Existing development worlds refuse at startup] → reset per `docs/development/database-reset.md`.

## Verification

`/tmp/mud-belts.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root, with `uv run --locked --env-file=/tmp/mud-belts.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_content_expansion_sites`, `world.maps.tests.test_bootstrap.test_bootstrap_grid`, `world.quests.tests.test_hunt_catalog_content`. Then run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.contract_gate --change north-deep-forest-placement` and `openspec validate north-deep-forest-placement --strict`.
