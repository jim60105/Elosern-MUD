# Proposal

## Why

Many test fixtures find "a materialized settlement room at a wilderness gateway face" by
taking the sorted-first row of the 虛境 city-gate registry. `retire-limbo-city-gates`
deletes that registry. Moving these probes first, to one shared probe that resolves to
the same node today, keeps the removal change small and makes this step easy to review:
no assertion should change.

## What Changes

- New helpers `entrance_refs(count)` and `first_entrance_ref()` in
  `world/tests/geography_fixture.py`. They return the first gate destination of the
  sorted-first wilderness entries, looked up by attribute string so that no shipped key
  is named.
- Every fixture that uses only the sorted-first gate row's node switches to
  `first_entrance_ref()`. Where a fixture checked that a gate row stood at a wilderness
  gate's room, it uses that gate's `destination` instead.
- The synthetic kit's borrowed first ref (`world/tests/synthetic_data/vocab.py`) reads
  the wilderness entry in the same way.
- No production code changes and no spec changes (`skip_specs: true`). Fixtures that
  depend on gate labels, on several gate maps, or on gate behavior stay as they are until
  `retire-limbo-city-gates`.

## Batch:

- depends-on: none. It can be applied at any point before `retire-limbo-city-gates`.
- Batch order: `subrace-start-locations`, `subrace-start-settlements`,
  `entrance-probe-fixtures` (this change), `retire-limbo-city-gates`,
  `drop-settlement-city-gate-field`.
- Conflict notes: `retire-limbo-city-gates` edits the same fixture files after this
  change: `world/rules/tests/test_map_knowledge_integration/_support.py`,
  `web/tests/browser/seed/*` and `world/tests/synthetic_data/vocab.py`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a test-only refactor with no behavior change.

## Impact

- Tests only. Files are listed in tasks.md.
- No human-reviewed document.
