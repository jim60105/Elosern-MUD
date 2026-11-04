# Proposal

## Why

Population projection currently predicts coordinate slots that do not yet exist. Sparse delayed populations require every visible entity and hostile interruption to come from current actual individuals.

## What Changes

- **BREAKING** Project only live registered individuals with stable object identities and remove prospective slot observations.
- Update area/local map, sight/travel comparison and GM inspection consumers while keeping undersupplied hunt habitat destinations separate.
- Reads remain side-effect-free and registry-derived threat/grade remains canonical.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `wilderness-population-view`: Revise the behavior contract in this change's delta.
- `wilderness-travel-interrupts`: Revise the behavior contract in this change's delta.
- `webclient-area-map`: Revise the behavior contract in this change's delta.

## Impact

`PopulationFact` already carries observation_key, cell, kind, hostile, label, threat_tier and danger_grade. `population_view` mixes expected ambient slots with real registered foreign entities. `travel_interrupts` and `presentation/area_map.py` read it, while GM `monsters.region_of` guesses region from the first ambient variant match.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: regional-population-owner

Code conflicts:
- regional-hunt-supply-cutover owns QuestDestination and habitat marker type edits; serialize its presentation tests with this slice.
- regional-population-runtime-cutover deletes remaining materializer helpers in wilderness_population.py after this read projection is independent.
- manual-monster-compositions changes site read semantics; filter actual position rather than assuming original site coordinates.
