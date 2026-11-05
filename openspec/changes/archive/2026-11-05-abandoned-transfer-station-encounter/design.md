# Design

## Context

See proposal.md (Why). After `site-member-activity-bindings`: `MonsterSite.activity_key` may be `None`, `CompositionMember.activity_key` binds a row, `composition_row_bindings(composition, site=site)` resolves rows, and site population forms one group per cohesive binding and one per solitary individual. `MonsterSite` is positional `(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_label_zh=None)`. A shipped site's composition must not be pooled by any zone (`test_every_shipped_composition_is_pooled_by_a_zone_or_owned_by_a_site`). Site population, clearing and recovery run inside the `monster_site_lifecycle` clock stage (`world/maps/monster_sites.py::settle_monster_sites_at`); `site_living_members` is the quest binding source. `engage_group(actor, targets)` in `world/rules/combat_session/lifecycle.py` opens one session against several present monsters.

Planning probe (map-core, `content/maps`): cell `(1290, 990)` is in `western_hills_valleys`, land and passable; the rectangle `(1285, 1295, 985, 995)` is 121/121 region-correct passable land; the nearest published location is `town_silver_ridge` at Chebyshev distance 221, and the site lies outside every zone added by `weak-species-habitats`.

## Goals / Non-Goals

**Goals:** the exact mixed encounter as a one-shot site with correct movement grouping and real-consumer evidence.

**Non-Goals:** recoverable or repeatable versions; quest definitions; any mechanism change; the boss sites.

## Decisions

### D1. Activity areas and activities

- Areas: `ActivityArea("transfer_station_grounds", "western_hills_valleys", ((1285, 1295, 985, 995),))`, `ActivityArea("transfer_station_nest", "western_hills_valleys", ((1286, 1290, 986, 990),))`, `ActivityArea("transfer_station_cache", "western_hills_valleys", ((1291, 1295, 991, 995),))`.
- Activities: `MonsterActivity("transfer_station_nest_activity", "cohesive_group", "transfer_station_grounds", 90, AggressionCondition("defended_area", "transfer_station_nest"))`; `MonsterActivity("transfer_station_stray_activity", "solitary_roaming", "transfer_station_grounds", 60, AggressionCondition("defended_area", "transfer_station_cache"))`.

### D2. Composition and site

```python
EncounterComposition(
    "abandoned_transfer_station_group",
    "transfer_station_nest_activity",
    (
        CompositionMember("hanging_nest_forager", 2, 2, activity_key="transfer_station_nest_activity"),
        CompositionMember("wax_cache_forager", 1, 1, activity_key="transfer_station_stray_activity"),
    ),
)
MonsterSite(
    "abandoned_transfer_station_encounter",
    "encounter",
    "western_hills_valleys",
    (1290, 990),
    "abandoned_transfer_station_group",
    None,
    3,
    True,
)
```

Place the composition in the manual-site block of `_ENCOUNTER_COMPOSITION_DECLARATIONS` and the site after `tide_mouth_boss_site`, each with an English comment stating co-location of independent animals and the one-shot lifecycle.

### D3. Production smoke module

New `world/maps/tests/test_content_expansion_sites.py`, first line `"""Data-contract test: content-expansion manual sites production smoke over the generic site, grouping, engagement and one-shot contracts`. Fixture: real wilderness with `ElosernWildernessMapProvider` and an initialized population seed, following `world/maps/tests/test_monster_sites.py::MonsterSiteLifecycleTests.setUp` but using the shipped registries (no registry patching); the site key is read once into a module constant `SITE_KEY` from the shipped registry by its key. Class `TransferStationEncounterTests`, observations naming their defects:
- Settling the site lifecycle at a tick populates the site's complete composition: three persisted individuals with distinct ids; the variants are the composition's rows (detects cycling/truncation).
- The site-owned groups in the activity record equal the shapes derived from the shipped declarations, `movement_units(<sampled rows>, composition_row_bindings(composition, site=site))`: same count, same member counts and same activity keys (detects whole-site grouping), without hard-coding member counts or variant keys in the test.
- `engage_group` from a player in that cell opens one session whose enemy roster holds all three ids (detects partial admission); each enemy is a distinct target.
- Defeating all three through the session settles one defeat per id in the kill accounting used by quest progress, a redelivered event adds nothing, and the site state becomes cleared (detects double credit or a lingering site).
- After a committed reload, a later clock settlement, a site-state read and a clear-out quest acceptance attempt, the site stays cleared and no individual is created (detects one-shot restoration).
Register the module once in a `maps-*` shard of `.github/evennia-shards.json` (next to `world.maps.tests.test_monster_sites`) and add its `tools/test_data_freeze.json` contract entry with the reason text of the first line.

### D4. Review documentation

Add "Content expansion sites" to `docs/development/regional-monster-population.md` (after the habitats subsection): why the cell reads as an abandoned transfer station on a hill transport route, co-location versus grouping, defended sub-areas, one-shot lifecycle, that all three share one cell only until their first independent decisions, a note that future repeatable content declares its own lifecycle and is never restored by quest acceptance or map observation, and the smoke commands/results. No coordinate repetition.

## Risks / Trade-offs

- [The groups roam independently once their first decisions fall due (60/90 ticks), and the site cell lies in the nest area but outside the rat's cache area] → whole-cell admission of all three is a property of the freshly populated site; the smoke engages before any decision is due, and D4 records this.

- [No quest commission names the site yet] → the quest-acceptance observation uses the existing clear-out binding read (`site_living_members`) to show nothing restores the site.

## Verification

Focused labels: `world.maps.tests.test_content_expansion_sites.TransferStationEncounterTests`, `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_population_geometry`. Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate abandoned-transfer-station-encounter --strict`, `uv run --locked python -m tools.contract_gate`.
