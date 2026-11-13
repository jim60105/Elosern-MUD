# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49` (re-locate by symbol name):

- `world/rules/clock.py::WorldClock.advance` builds `registry = build_advance_snapshot_registry(...)`, runs `_run_stages` inside `transaction.atomic()`, and on any exception calls `_restore_clock_tick` and `_restore_advance_registry(registry, scope)`.
- The registry merges `population_lifecycle.snapshot_population_lifecycle_surfaces`, which is the union of `monster_sites.snapshot_monster_site_surfaces`, `regional_population.snapshot_regional_population_surfaces` and `monster_activity.snapshot_monster_activity_surfaces`. Together they cover: the wilderness attributes `monster_activity`, `regional_population`, `regional_population_seed`, `itemcoordinates`, `population_timeline`, `population_zone_scope`, `monster_sites`; and for every tracked individual `traits`, `FATIGUE_ATTRIBUTE_SURFACES`, `SLEEP_RECEIPT_SURFACES`, `site_key` and `location`. Individuals created during the advance are removed by the rollback and evicted by `flush_orphan_instances()`.
- Per-operation protection sites:
  - `monster_activity._commit_stay`: `snapshot_activity_surfaces(...)`, `transaction.atomic()`, `restore_activity_surfaces` in `except`.
  - `monster_activity._commit_departure`: `snapshot_group_decision_surfaces(...)`, `transaction.atomic()`, `restore_activity_surfaces` in `except`.
  - `fatigue.settle_fatigue_intervals`: one `attribute_snapshot` per surface per body, `transaction.atomic()`, `restore_attribute_best_effort` in `except`.
  - `regional_population.commit_population_wave`: passes `snapshot=snapshot_population_surfaces(wilderness)` to `_commit_planned_wave`, which opens `transaction.atomic()` and restores when `snapshot is not None`. `_commit_planned_wave` already documents `snapshot=None` as "an enclosing owner operation already holds the rollback surface".
  - `monster_sites.settle_site_recovery`: `states_before`, `snapshot_population_surfaces(wilderness)`, `transaction.atomic()`, restore in `except`.
- Inside a pass no caller catches an exception from these five operations and continues: `monster_activity.settle_group_decisions_at`, `_settle_due_journeys`, `regional_population.settle_recovery_due` and `monster_sites.settle_monster_sites_at` have no such handler; `monster_activity._settle_interval` logs and re-raises.
- The one place that recovers and continues is the contact block in `population_lifecycle._settle_population_at`, already wrapped in `monster_activity.unbatched_state_writes()`. `world/rules/field_contact.py` restores its participants and returns.
- Tests call `settle_population_lifecycle` directly, outside any advance. There the operations must keep their own protection.

## Goals / Non-Goals

**Goals:**

- One explicit flag that is true only while a lifecycle pass runs inside `WorldClock.advance`.
- The five sites consult that flag and nothing else.

**Non-Goals:**

- No change to the registry builder, to `_restore_advance_registry`, or to any `snapshot_*_surfaces` contract.
- No change for callers outside the lifecycle pass: `_settle_mental`, combat settlement, `world/rules/action/transaction.py`, `world/rules/combat_initiation.py`, GM verbs.
- No change to `world/rules/field_contact.py`.
- No removal of any snapshot or restore function; they stay for the direct path.

## Decisions

### D1. Flag in `world/rules/surfaces.py`

Add to `world/rules/surfaces.py`:

```python
_OUTER_ROLLBACK: bool = False


@contextmanager
def outer_rollback_owner() -> Iterator[None]:
    """Declare that an enclosing owner restores every surface the enclosed work writes."""


@contextmanager
def suspended_outer_rollback() -> Iterator[None]:
    """Run the enclosed work with its own protection, then resume the owner."""


def outer_rollback_active() -> bool:
    """Whether an enclosing owner currently holds the rollback."""


def owned_atomic() -> AbstractContextManager[Any]:
    """``contextlib.nullcontext()`` under an outer owner, else ``transaction.atomic()``."""
```

Both context managers restore the previous value in `finally`. A plain module global is used, like `monster_activity._ACTIVE_BATCH`: settlement is synchronous on the reactor thread.

### D2. The clock says when a registry is held

Add to `world/rules/clock.py` a module global `_ADVANCE_REGISTRY_HELD: bool = False` and a public function `advance_registry_held() -> bool`. In `WorldClock.advance`, set it to `True` immediately before `with transaction.atomic():` and restore the previous value in the existing `finally`. `advance_bounded` needs no edit (it calls `advance`).

### D3. The pass opens the owner scope

In `population_lifecycle.settle_population_lifecycle`, add one more manager to the pass's `with` block:

```python
outer_rollback_owner() if advance_registry_held() else nullcontext(),
```

In `_settle_population_at`, the contact block adds `suspended_outer_rollback()` to its `with` statement next to `unbatched_state_writes()` and `suspended_maintenance_tally()`.

A direct call of `settle_population_lifecycle` (tests, tools) has no registry and therefore keeps per-operation protection. This is also the reference path of the differential test.

### D4. The five sites

For each site, the rule is the same three edits:

1. Take the snapshot only when `not outer_rollback_active()`; otherwise bind the snapshot variable to `None`.
2. Replace `with transaction.atomic():` by `with owned_atomic():`.
3. In `except`, restore only when the snapshot variable is not `None`; always re-raise.

Site details:

- `_commit_stay`, `_commit_departure`: guard `restore_activity_surfaces(snapshot, wilderness=wilderness)`.
- `settle_fatigue_intervals`: build `snapshots` as an empty list under the owner; the `except` loop then restores nothing.
- `commit_population_wave`: pass `snapshot=None if outer_rollback_active() else snapshot_population_surfaces(wilderness)`; in `_commit_planned_wave` replace `transaction.atomic()` by `owned_atomic()`.
- `settle_site_recovery`: under the owner skip `states_before` and `surfaces`; in `except` skip `_write_state(wilderness, states_before)` and `restore_population_surfaces(surfaces)`.

Do not touch `regional_population.initialize_zones` (line 2277 region): it is not called from a pass.

### D5. Tests

New `world/maps/tests/test_settlement_outer_rollback.py`, on `ActivityFixture` from `world.maps.tests.test_monster_activity`, using `settlement_projection` from `world/maps/tests/_settlement_projection.py` and `self._register_lifecycle()`; advances go through `get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])`.

- `world/rules/tests/test_surfaces_outer_rollback.py` is not needed; put the four pure flag tests (default false, owner true, suspension false then true again, exception restores) in the new module as a `unittest.TestCase` class.
- "Savepoints do not grow with the population": `CaptureQueriesContext(connection)`; count statements whose SQL starts with `SAVEPOINT`. Compare one group against four groups due in the same interval.
- "Fault after a partial departure": `patch.object(regional_population, "record_population_transition", side_effect=RuntimeError)` during an advance whose interval contains a departure built with the fixture's `_departure_seed`. Compare `settlement_projection` before and after, the source room's `contents`, and attributes re-read after `attributes.reset_cache()`.
- "Fault during a fatigue write": wrap `world.rules.fatigue.write_fatigue_state` so the second call raises.
- "Results are unchanged": `run(parts, owned)` rebuilds the scenario after `self._reset_activity(tick=100)` and sets `get_world_clock().tick = 100`; `owned=False` patches `world.maps.population_lifecycle.outer_rollback_owner` with `contextlib.nullcontext`. Compare projections for `(1500,)` and `(700, 800)` in both modes.
- "Direct operation outside an advance": existing tests `world.maps.tests.test_monster_journeys` and `world.rules.tests.test_world_escape` already cover it; run them, add nothing unless one of them stops covering a direct departure failure.
- "Failed contact inside a pass": model on the existing contact failure test found by `grep -n "field_contact_failed" world/rules/tests/*.py`; run that scenario through `clock.advance` and assert the advance returns, the participants equal their pre-contact snapshot and the due group's sequence advanced.

### D6. Documentation

Add a section "Rollback ownership inside an advance" to `docs/development/monster-field-behaviour.md`: the flag, who opens it, the five sites, the contact exception, and the rule that a new lifecycle operation that recovers and continues must run under `suspended_outer_rollback()`.

## Risks / Trade-offs

- [A surface written by a pass operation is missing from the advance registry, so its cache stays stale after a rollback] → the two fault scenarios compare caches and reloaded values; the context section lists the coverage that was checked. If a fault test shows a surface the registry misses, stop and report: the fix belongs in the owning `snapshot_*_surfaces` contract, not in re-adding a per-operation snapshot.
- [A future pass operation catches an exception and continues without suspending the owner, leaving partial writes] → documented rule in D6; the differential test does not catch this, so reviewers must.
