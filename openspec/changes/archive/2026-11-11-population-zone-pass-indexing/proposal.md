# Proposal

## Why

The near-settlement monster programme raises the shipped ecology zones from 9 to about 165 and the standing ambient population from about 40-100 to roughly 1,200-2,500 individuals. Wave 1 alone adds 91 zones. Today every boundary zone pass multiplies those two numbers. `regional_population.note_population_boundaries` calls `counts_from_presence` once per zone, and each call iterates every presence fact in the world. `_boundary_fields` then calls `zone_state`, which decodes the whole per-zone state attribute again for each zone. The lifecycle coordinator (`population_lifecycle._settle_population_at` and `_next_population_boundary`) decodes the full state map once per zone as well. The forecast (`population_forecast._Projection._note_zone_boundary`) repeats the whole-presence scan for each zone three times per projected step, and a projection can run up to `MAX_PROJECTION_STEPS` steps.

The zone pass therefore costs O(zones × individuals + zones²) per boundary. With 9 zones and about 40 individuals that is a few thousand fact visits. With 100 zones and about 600 individuals it grows to roughly 60,000 fact visits per note pass and 10,000 record decodes per boundary, which multiplies the documented per-boundary settlement cost (`docs/development/evennia-test-performance.md`, 0.17 s local per boundary today). This change makes one boundary zone pass linear: one state decode and one presence scan per pass, whatever the zone count. Observable behaviour does not change.

## What Changes

- `world/maps/regional_population.py`: a batch zone-count reader that scans presence once for many zones; a batch zone-state reader that decodes the state map and the world seed once; `note_population_boundaries` uses both; a `due_recovery_zone_keys` reader returns the zones whose recovery is due at a tick.
- `world/maps/population_lifecycle.py`: the per-boundary recovery loop visits only due zones, and the next-boundary query reads every zone's due tick from one decode.
- `world/maps/population_forecast.py`: snapshot capture reads zone states from one decode, and each projected zone note uses one presence scan.
- New synthetic mechanism tests prove the work-set sizes by call counts. No test measures time.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `regional-population`: adds one requirement. A boundary zone pass reads the shared state map and presence facts once per pass, whatever the zone count, with results equal to the per-zone reads.

## Impact

Code: `world/maps/regional_population.py`, `world/maps/population_lifecycle.py`, `world/maps/population_forecast.py`. Tests: new `world/maps/tests/test_population_zone_pass.py`, registered once in `.github/evennia-shards.json`. No data, map, content, protocol or persistence-shape change, and no migration. Existing callers of `zone_state`, `counts_from_presence` and `note_population_boundary` keep their signatures and results.

Out of scope, recorded for the supervisor: activity-group decision work stays proportional to the number of groups by design (every group decides on its own cadence), and fresh wilderness provisioning creates the whole standing population at once, so test fixtures that call `world.tests.geography_fixture.sync_test_wilderness` will create more individuals after the placement waves land. Neither cost involves a zone-by-individual cross term. Changing either one is a separate design decision.

## Batch:

No dependencies: this change only reads registries that already ship.

Wave 1, first change. Every Wave 1 placement change (`eastern-plains-near-belts`, `western-hills-near-belts`, `coastal-near-belts`, `highland-road-belts`, `north-deep-forest-placement`) depends on it. No file conflict with the species changes.
