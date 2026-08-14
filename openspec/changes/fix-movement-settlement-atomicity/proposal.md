## Why

Evennia persists a successful location change before `Exit.at_post_traverse` runs. Elosern's post-traverse hook (`after_successful_movement`) advances the world clock first and only then records arrival, follows companions, and runs onboarding. When the mandatory clock charge fails, the exception propagates after relocation: the WebClient reports `move_failed` even though the player already stands in the destination, while world time, map knowledge, companions, and onboarding state remain behind (security-audit run-3 finding index 2, confirmed by dynamic probes).

## What Changes

- Introduce a deterministic movement-settlement boundary in `world/rules/movement_settlement.py` that wraps relocation, clock charging, map-knowledge recording, companion following, and onboarding observation in one outer database transaction and, on any failure, compensates the already-persisted relocation and reconciles Evennia's in-process caches — in-memory `db_location`, source/destination `contents_cache`, attribute caches, quest-observation surfaces (`quest_log`, room `pin_reasons`/`interacted`), and wilderness script bookkeeping (`itemcoordinates`, `rooms`, `unused_rooms`) — before surfacing the failure.
- `MovementCostMixin` gains an `at_traverse` override that opens the boundary around the stock traversal; `WildernessGateExit` and `WildernessReturnExit` route their traversal bodies through the same boundary, and their falsy-return-with-relocation case (a `move_to` hook raising after relocation on a lineage that returns a real boolean) is compensated as a failure. `at_post_traverse` and the shared `after_successful_movement` ordering are unchanged.
- The boundary consumes the parallel `fix-clock-rollback-cache-sync` change's `build_advance_snapshot_registry` seam (forward-declared until that change lands) so clock callback-owned surfaces are covered whichever transaction boundary fails; the two changes stay non-overlapping.
- A failed movement therefore leaves the player at the source room with clock, map knowledge, party, quest state, and onboarding coherent; `move_failed` (WebClient) and the propagated error (Telnet `ExitCommand`, scene command) become truthful.
- Correct the `after_successful_movement` docstring, which currently claims every helper "never raise[s] from a traversal hook" — `charge_movement` can raise.

## Capabilities

### New Capabilities

- `movement-settlement-atomicity`: the outer movement settlement boundary, its compensation semantics, and the truthful-failure guarantee for every exit lineage and client path.

### Modified Capabilities

- `movement-cost-charging`: the `MovementCostMixin` requirement changes from "SHALL NOT override `at_traverse`" to "SHALL override `at_traverse` only to open the settlement boundary"; charging still flows through `at_post_traverse` → `after_successful_movement` → `charge_movement`, unchanged.

## Impact

- `world/rules/movement_settlement.py` (new): settlement snapshot (locations, companions, wilderness bookkeeping, quest-observation and advance surfaces), outer transaction, falsy-return trigger, compensation, cache reconciliation.
- `typeclasses/exits.py`: `MovementCostMixin.at_traverse` wrapper; `WildernessGateExit`/`WildernessReturnExit` bodies routed through the boundary; docstring fixes.
- `world/rules/clock.py`: consumed read-only via the `build_advance_snapshot_registry` seam (lands with the parallel `fix-clock-rollback-cache-sync` change; forward-declared with a guarded test until then) — no production change in this change.
- `world/rules/map_knowledge.py`, `world/rules/party.py`, `world/rules/onboarding.py`: unchanged; their functions are the steps the boundary wraps.
- `world/quests/transitions.py`: read-only reuse of the existing `snapshot_quest_log`/`restore_quest_log`/`snapshot_pin_reasons`/`restore_pin_reasons` helpers — no production change.
- `web/webclient/actions/exploration_actions.py`: no production change; the `move_failed` contract stays, and tests assert the compensated state.
- `commands/scene.py` (scene-door traversal) and Telnet `ExitCommand` inherit the boundary automatically because they call `at_traverse`.
- Tests: new `world/rules/tests/test_movement_settlement.py` plus additions to `typeclasses/tests/test_exit_movement_cost.py` and `web/webclient/actions/tests/test_exploration_actions.py`.

Related, non-overlapping parallel changes: `fix-cast-clock-settlement` (outer settlement around out-of-combat cast) and `fix-clock-rollback-cache-sync` (clock snapshot/restore completeness for callback-owned surfaces, whose D6 mandates the registry seam this change consumes). This change is scoped to movement only and does not design either change's internals.
