# Proposal

## Why

`monster-activity-record-parts` changes how the monster-activity record is stored. About twenty test statements in ten test modules read or assign `wilderness.db.monster_activity` directly, so they depend on the stored form being one mapping. Changing the stored form and rewriting those tests in one change is more than one day of work and mixes a behaviour-neutral edit with a storage change.

This change removes that dependency first, on the present stored form, so the storage change that follows touches the owner module and its own new tests only.

## What Changes

- Two public functions in `world/maps/monster_activity.py`, on the present stored form: `write_monster_activity(wilderness, state)` and `read_stored_monster_activity(wilderness)`.
- Every test that assigns `wilderness.db.monster_activity = state_to_dict(...)` writes through `write_monster_activity`; every test that reads `dict(wilderness.db.monster_activity)` as a before/after value compares `state_to_dict(read_stored_monster_activity(wilderness))`.
- No production caller, no stored format, no settlement outcome and no requirement changes. The change declares `skip_specs: true`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behaviour changes.

## Impact

- Code: `world/maps/monster_activity.py` (two functions, `__all__`).
- Tests: `world/maps/tests/test_monster_activity.py`, `test_monster_journeys.py`, `test_population_drain.py`, `test_population_units.py`, `test_settlement_outer_rollback.py`, `test_regional_population.py`, `test_monster_sites/test_site_population.py`, `world/rules/tests/test_field_contact_boundaries.py`.
- Human-reviewed: none.

## Batch:

- depends-on: none
- This change does not require commit `c0736d44` (`fix/population-group-units-memo`). That commit also edits `world/maps/tests/test_population_units.py` in a different place; keep both edits.
- conflicts: `monster-activity-record-parts` rewrites the two functions this change adds and is ordered directly after it. `population-drain-idle-gate` also edits `world/maps/tests/test_population_drain.py` (different lines: its fixture `setUp` and the periodic-caller class); run them serially in either order.
- parallel with: none of this batch.
