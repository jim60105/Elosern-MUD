# Design

## Context

See proposal.md (Why). Facts at `1b1be7b8` plus the batch-1/2 changes:

- `EcologyZone(key, region_key, rectangles, pool, lower_density, upper_density, cell_capacity, recovery_delay, replenishment_interval, wave_budget)`; shipped zones use `((x0, x1, y0, y1),)` 20×20 rectangles and `(1, 3, 3, 3600, 600, 3)` for the six trailing integers. `validate_ecology_registries` and `world.maps.population_geometry.validate_ecology_geometry` enforce region intersection, map validity, settlement exclusion, `upper_density < 100`, complete-composition recoverability and that each pooled variant's species declares the zone's region as a habitat tag.
- `EncounterComposition(key, activity_key, members)`; `CompositionMember(variant_key, minimum, maximum, activity_key=None)`.
- `ActivityArea(key, region_key=None, rectangles=(), home_radius=None)`; `MonsterActivity(key, policy, area_key, decision_interval, aggression)`; `AggressionCondition(kind, area_key=None, dayparts=())`. Shipped roaming activities use interval 60 (solitary) and 90 (cohesive).
- After `activity-group-formation`, a `solitary_roaming` binding may cover a multi-member composition and each individual forms its own group at birth.
- Planning probe (map-core `terrain_definition` over `content/maps`, run during proposal): every rectangle below is 400/400 cells inside its region, land and passable, and its nearest published location or harbor is at least the stated Chebyshev distance away.

| Zone (key) | Region | Rectangle `(x0, x1, y0, y1)` | Nearest point, distance | Inland water cells within 3 |
| --- | --- | --- | --- | --- |
| `eastern_mudbank_habitat` | `eastern_plains` | `(2060, 2079, 820, 839)` | `city_twin_currents`, 112 | 26 |
| `western_mudbank_habitat` | `western_hills_valleys` | `(300, 319, 840, 859)` | `kingdom_western_secondary_port`, 140 | 25 |
| `western_quarry_habitat` | `western_hills_valleys` | `(620, 639, 560, 579)` | `city_salt_ferry`, 215 | 0 |
| `eastern_cache_habitat` | `eastern_plains` | `(1580, 1599, 520, 539)` | `town_orange_blossom`, 206 | 0 |
| `western_cache_habitat` | `western_hills_valleys` | `(820, 839, 720, 739)` | `town_honey_vale`, 201 | 0 |

These are planning inputs; the declarations become the only authority once written. Do not repeat this table in documentation or tests.

## Goals / Non-Goals

**Goals:** bounded sparse birth habitats and field activity for the three weak species.

**Non-Goals:** manual sites (owned by the transfer-station and boss-site changes); settlement birth policies; quest commissions; any new mechanism or validator.

## Decisions

### D1. Activity areas (append to `_ACTIVITY_AREA_DECLARATIONS`)

Grounds equal to each zone rectangle: `ActivityArea("eastern_mudbank_grounds", "eastern_plains", ((2060, 2079, 820, 839),))`, `ActivityArea("western_mudbank_grounds", "western_hills_valleys", ((300, 319, 840, 859),))`, `ActivityArea("western_quarry_grounds", "western_hills_valleys", ((620, 639, 560, 579),))`, `ActivityArea("eastern_cache_grounds", "eastern_plains", ((1580, 1599, 520, 539),))`, `ActivityArea("western_cache_grounds", "western_hills_valleys", ((820, 839, 720, 739),))`.

Defended sub-areas (6×6, centred): `ActivityArea("western_quarry_nest", "western_hills_valleys", ((627, 632, 567, 572),))`, `ActivityArea("eastern_cache_store", "eastern_plains", ((1587, 1592, 527, 532),))`, `ActivityArea("western_cache_store", "western_hills_valleys", ((827, 832, 727, 732),))`.

### D2. Activities (append to `_ACTIVITY_DECLARATIONS`)

- `MonsterActivity("eastern_mudbank_dweller_activity", "solitary_roaming", "eastern_mudbank_grounds", 60, AggressionCondition("passive"))` and the `western_` twin over `western_mudbank_grounds`.
- `MonsterActivity("western_quarry_nest_forager_activity", "cohesive_group", "western_quarry_grounds", 90, AggressionCondition("defended_area", "western_quarry_nest"))`.
- `MonsterActivity("eastern_cache_forager_activity", "cohesive_group", "eastern_cache_grounds", 90, AggressionCondition("defended_area", "eastern_cache_store"))` and the `western_` twin with `western_cache_grounds`/`western_cache_store`.

### D3. Compositions (append to `_ENCOUNTER_COMPOSITION_DECLARATIONS`, before the manual-site block)

`EncounterComposition("eastern_mudbank_dweller", "eastern_mudbank_dweller_activity", (CompositionMember("mudbank_dweller", 1, 3),))`, its `western_` twin; `EncounterComposition("western_quarry_nest_forager", "western_quarry_nest_forager_activity", (CompositionMember("hanging_nest_forager", 2, 4),))`; `EncounterComposition("eastern_cache_forager", "eastern_cache_forager_activity", (CompositionMember("wax_cache_forager", 2, 5),))` and its `western_` twin.

### D4. Zones (append to `_ECOLOGY_ZONE_DECLARATIONS`)

One zone per table row with `pool=(WeightedComposition(<its composition>, 1),)`. Start from the shipped trailing values; raise `cell_capacity` and `wave_budget` to at least the composition's maximum (3, 4 and 5 respectively) and keep `upper_density` high enough that `validate_ecology_registries`' complete-recovery rule passes. Adjust only what validation requires and record why in the review subsection.

### D5. Review documentation

Add "Content expansion habitats" under "Authoring review (human judgment)" in `docs/development/regional-monster-population.md`: per zone, the dossier fact it serves and why the rectangle's terrain (inland water for the slime; remote dry hills for the goblin quarry; plains margin and hill transport ground for the rats) fits; the passive/defended-area choice; that no high-tier variant joins an ordinary pool; and the commands/results of D6. No coordinate, density or count is copied there (the existing rule of that section).

## Risks / Trade-offs

- [Published geography carries no explicit quarry or granary feature] → the rectangles are remote, passable, region-correct candidates; the human review decides fidelity and may move a rectangle within the same constraints without any test edit.
- [Five zones increase background population] → each zone is sparse and bounded; the density interval is the single source.

## Verification

Focused labels (one per run, `/tmp/mud-field-tests.env` with `MUD_TEST_SETTINGS=1`, `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <label>`): `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_bootstrap`, `world.maps.tests.test_regional_population`. Then `uv run --locked python -m tools.map_reference_context` and `--check`, `openspec validate weak-species-habitats --strict`, `uv run --locked python -m tools.contract_gate`.
