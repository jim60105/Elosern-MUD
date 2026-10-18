# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Skip scope (2h)

- [x] 1.1 Make `world/rules/time_skip.py::advance_skip` pass `present_party_scope(actor)` and keep its booking restore on failure; verify in `world/rules/tests/test_party_time_settlement.py` that a one-hour rest regenerates a co-located companion's MP/SP/HP by her own rate, expires her short buff, leaves a companion in another room untouched, and that `sleep` still derives its duration from the caller only.

## 2. Movement scope (2.5h)

- [x] 2.1 Change `charge_movement` to take `source_location` (and wilderness source coordinates), compute the travelling party with the follow predicate, and update `typeclasses/exits.py::after_successful_movement` to pass them; verify grid, wilderness step and gate-entry traversals settle followers, a companion elsewhere is untouched, a possessed traversal settles the traverser, the owner body and co-located companions, and the flight waiver still skips the advance.
- [x] 2.2 Extend `world/rules/movement_settlement.py` so the snapshot registry and `_restore_advance_registry` cover the same travelling party; verify with an injected clock failure that every member's gauges/buffs and the tick are restored and the traverser is compensated back to the source.

## 3. Unchanged scopes and observability (1h)

- [x] 3.1 Add regression assertions that church (`world/rules/church.py`), GM console, defeat aftermath and `settle_combat_result` call sites pass their existing entity tuples; add `scope` to the clock-advance context at the widened call sites and run `uv run --locked python -m tools.observability_lint check` with the focused event test.

## 4. Integration (1.5h)

- [x] 4.1 Update existing movement/skip tests that pinned a one-entity tuple, register the new module in exactly one shard, and run the focused labels plus `tests.test_evennia_test_optimization_contract`.
- [x] 4.2 Annotate with canonical IDs (`party-time-settlement`, `movement-cost-charging::charge_movement-is-the-single-shared-movement-cost-charging-function` style IDs from `tools.spec_traceability list`), run `uv run --locked python -m tools.contract_gate` and `openspec validate party-rest-move-settlement --strict`.
