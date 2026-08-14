## Why

`CmdCast._cast_out_of_combat` commits the skill effect, practice award, and planner writes inside `ActionResolver.resolve`'s transaction (world/rules/action.py:1068-1098, 1141-1175), then charges the world clock in a separate `WorldClock.advance` transaction (world/rules/clock.py:316-337). Neither project code nor Evennia's command handler wraps `CmdCast.func` in an outer transaction, so a clock callback or persistence failure — or a process stop between the two transactions — leaves the already-committed action durable without its time cost, with in-process caches diverging from the rolled-back rows (security-audit run-3 finding index 6, severity low: a clock fault is uncommon and all seven ACTIVE out-of-combat catalog skills have empty resource costs).

## What Changes

- Introduce a deterministic out-of-combat command-settlement API (`world/rules/cast_settlement.py`) that snapshots all action- and clock-touched objects before resolution, opens one outer transaction, invokes `ActionResolver.resolve` and `WorldClock.advance` as nested operations, commits only after both succeed, and on failure restores the pre-action Evennia Attribute/trait/sexual-state/target/planner-owned/callback-owned/clock caches before propagating.
- `CmdCast._cast_out_of_combat` delegates to the API; success rendering happens only after the outer commit. The in-combat session path (`_cast_in_session`) is untouched.
- The settlement consumes the `build_advance_snapshot_registry` seam plus clock-tick snapshot/restore exactly as mandated by `fix-clock-rollback-cache-sync`'s design D6 (forward-declared with guarded tests until that change lands), so callback-owned surfaces are covered when the cast's outer boundary fails.
- Add regression tests covering clock-callback failure, final-persistence failure, and commit-window (process-stop surrogate) compensation, for `status_disguise` and at least one buff-applying out-of-combat spell, plus success/restart coherence and an unchanged in-combat path.

## Capabilities

### New Capabilities

- `cast-settlement-atomicity`: the outer out-of-combat cast settlement boundary — pre-resolution snapshot superset, single outer transaction, nested resolve/advance, all-or-nothing restore of every touched Evennia cache, and post-commit-only success rendering.

### Modified Capabilities

- `world-clock`: the "CmdCast advances command time only outside a persistent combat session" requirement changes from two sequential transactions to one outer settlement transaction; the charge itself (`AdvanceSource.COMMAND`, `[actor]` scope, no advance on rejection) is unchanged.

## Impact

- `world/rules/cast_settlement.py` (new): settlement API, snapshot superset (actor, request targets, optional battlefield, merged advance registry, clock tick), outer transaction, deterministic restore.
- `commands/action.py`: `_cast_out_of_combat` delegates to the settlement API; context construction (including the `status_disguise` disguise payload) and in-combat delegation are unchanged.
- `world/rules/clock.py` and `world/rules/action.py`: consumed read-only (advance, `_ADVANCE_ENTITY_SURFACES`, `_snapshot_advance_entities`, `_snapshot_clock_tick`/`_restore_clock_tick`, and the `build_advance_snapshot_registry` seam that lands with `fix-clock-rollback-cache-sync`) — no production change in this change.
- `world/rules/surfaces.py` (shared snapshot/restore dispatch) and `world/quests/transitions.py` (quest-log restore helpers): read-only reuse.
- Tests: new `world/rules/tests/test_cast_settlement.py`, plus additions to `commands/tests/` command-surface tests.
- Depends on `fix-clock-rollback-cache-sync` (lands after it; the registry seam is forward-declared until then) and is related-but-non-overlapping with `fix-movement-settlement-atomicity` (that change owns the movement post-traverse outer boundary; this change is scoped to the out-of-combat cast command path only).
- No dependency, migration, or data-schema impact; the project has no released users.
