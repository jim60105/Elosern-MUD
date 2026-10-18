# Tasks

Total estimate: **5 hours**, including implementation, focused verification, documentation and integration.

## 1. Cast settlement scope (2h)

- [x] 1.1 Pass `present_party_scope(request.actor)` to the snapshot, advance and restore in `world/rules/cast_settlement.py`; verify in `world/rules/tests/test_party_time_settlement.py` that a commander field cast regenerates a present companion, leaves a companion elsewhere unchanged, and that an injected failure after the advance restores both members' gauges/buffs and the tick.

## 2. Item use settlement scope (1.5h)

- [x] 2.1 Do the same in `world/rules/items/settlement.py`; verify a successful potion use settles the present party once, a rejected use settles nobody, and a clock-callback failure restores the item, both members and the tick.

## 3. Integration (1.5h)

- [x] 3.1 Update existing cast/item settlement tests that asserted the single-entity tuple, add the `scope` context to the clock-advance event with a focused event assertion, and run `uv run --locked python -m tools.observability_lint check`.
  No existing cast/item settlement test pinned the single-entity tuple; the four `_snapshot_settlement_state` call sites now pass the scope explicitly. The clock-advance `scope` context already existed from `party-rest-move-settlement`; the new cast and item tests assert it directly.
- [x] 3.2 Annotate tests with canonical IDs for the modified `cast-settlement-atomicity`, `item-use-resolution` and `world-clock` requirements and the added `party-time-settlement` requirement, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate party-field-settlement-scope --strict`.
  The added requirement's canonical ID is recorded in the test-module docstring; its `covers_requirement` decorator lands with the archive/sync step, per the `party-member-authority` precedent, because traceability indexes only `openspec/specs/`.
