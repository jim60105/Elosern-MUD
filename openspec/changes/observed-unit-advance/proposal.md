# Proposal

## Why

Every clock advance settles the monster population of the whole world, so the cost of one player action grows with the world-wide monster count. Even after the three settlement cost changes of this batch make today's world fast enough, the cost keeps growing with the world, and the freeze returns as the world grows. The cost of a player action must not depend on the total world population.

`population-settlement-units`, `unit-scoped-population-settlement` and `population-catch-up-entry-points` prepared the ground: independent units, scoped settlement proven equal to whole-world settlement, and catch-up at every entry point. This change switches the clock stage: an advance settles only the observed units. Every other unit stays at its own settled-through tick until it is observed, an entry point catches it up, or the background drain of `population-backlog-drain` reaches it. Outcomes are unchanged, because any partition of the same elapsed interval yields the same result per unit; only the moment the work is done changes.

This work is mandatory. No measurement decides whether it happens. Timings may be recorded as information only.

## What Changes

- **BREAKING (internal contract)** The registered population stage settles the observed units only. A unit that is observed while behind is first caught up, inside the same advance, to the advance's start.
- The advance's snapshot registry and the contact forecast (`next_population_lifecycle_boundary`) are limited to the observed units. The living-individual scan follows in `observed-unit-read-narrowing`; until then it reads the whole world once per pass, which is correct and only costs time.
- The whole-world pass remains available as a function for tools and tests; it is no longer the clock stage.
- Existing tests that advance the clock and then assert the state of unobserved groups catch the world up before asserting.
- The design documents are amended (see Impact): unobserved monsters still act on game time with the same outcomes, but their settlement is materialised when they are observed.
- World saves need no change: a save stores each unit's settled-through tick, and a restored world continues from there.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: a clock advance settles observed units only, with work independent of unobserved units.
- `monster-field-activity`: the unobserved-activity scenario states when the result becomes stored.

## Impact

- Edits: `world/maps/population_lifecycle.py`, `world/maps/population_units.py`, `world/maps/monster_sites.py` (snapshot contract only), `world/maps/population_forecast.py`.
- Tests: new `world/maps/tests/test_observed_unit_advance.py` (registered in `.github/evennia-shards.json`); a helper `catch_up_world` in `world/maps/tests/_settlement_projection.py`; mechanical edits in existing tests that fail (design D6).
- Design documents amended in this change:
  - `docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md` §1 (row "Simulation") and §5.2;
  - `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md` (timing rule);
  - `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §6.5 (world clock).
  The main design's decision D4 (player-driven clock) is not changed: no world time passes without a player action.
- Development documentation: `docs/development/regional-monster-population.md`, `docs/development/monster-field-behaviour.md`.
- Known limit: a unit that was unobserved for a long game time is caught up in one synchronous step when first observed. Its cost grows with that unit's lag, not with the world. `population-backlog-drain` pays lag off between commands; a long time skip followed at once by travel into another unit still pays that unit's whole lag in one step.

## Batch:

- depends-on: population-writer-guards
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
