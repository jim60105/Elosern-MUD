# Design

## Context

See `proposal.md` for the motivation. This design assumes commit `c0736d44` and the changes `population-drain-idle-gate`, `monster-activity-record-parts` and `population-snapshot-part-scoping` are merged.

Current code:

- `world/maps/population_drain.py::drain_population_backlog(slice_seconds) -> bool` reads the wilderness, the world tick, the cursor record and `population_units.lagging_sets(wilderness, now)` (pairs `(cursor, units)` sorted by `(cursor, min(units))`). It walks `pending[:MAX_SETS_PER_RUN]` (3): for each set it builds the scope, builds the rollback registry, opens `held_advance_registry()` and `transaction.atomic()`, calls `population_lifecycle.settle_population_scope(wilderness, units, target, contact=False)` and schedules the `population_backlog_drained` event on commit. A failure restores the registry, logs `population_backlog_drain_failed` and continues with the next set. The first success returns `True`.
- `_units_still_lagging(pending, cursors, settled, target, now)` counts the units behind `now` after one settlement.
- `PopulationDrainScript.at_repeat` (after `population-drain-idle-gate`): enable switch, idle window, then `drain_population_backlog(settings.POPULATION_DRAIN_SLICE_SECONDS)`.
- `world/maps/population_units.py::group_units_map(index, state)` builds a new dict of every group's units on each call. Callers: `closed_sets` (from `lagging_sets`), `build_scope`, `unit_closure`, `warm_group_units`. `_area_units` (commit `c0736d44`) memoizes the costly part per resolved area, so one call is now a cheap loop over every group, but a drain step still runs it three times: `lagging_sets`, the drain's `build_scope`, and `settle_population_scope`'s `build_scope`. `ensure_population_current` runs it twice.
- `monster_activity.read_monster_activity` returns the same immutable `MonsterActivityState` object until the record is written (identity memo), so `lagging_sets` and `build_scope` already share one decode.
- A scoped pass writes only inside its closed set (`require_units_in_active_scope`, `require_in_active_scope`), and `group_units` is a pure function of the group, its journey, the unit index (pinned to the published registries) and the published geography.

## Goals / Non-Goals

**Goals:**

- One run pays several unit-slices under a bound stated as a count of steps.
- One group-units computation per unchanged activity record.

**Non-Goals:**

- No change to `settle_population_scope`, `_run_pass`, `ensure_population_current`, `lagging_sets`' signature or result, `build_scope`'s signature or result, the events' names or fields, or the per-step transaction and rollback.
- No longer pass per step: a step never settles more than one slice.
- No bound stated in real time, and no test of real time.
- No thread, no process, no yield to the reactor inside a run.

## Decisions

### D1. Steps per run

Replace `MAX_SETS_PER_RUN` with:

```python
#: How many failed sets one run tolerates before it yields to the reactor.
MAX_FAILED_SETS_PER_RUN = 3
```

New signature:

```python
def drain_population_backlog(slice_seconds: int, max_steps: int = 1) -> int:
    """Settle lagging closed sets forward, one slice per step.

    Performs at most ``max_steps`` settlement steps and returns how many
    settled. Each step selects the set with the lowest cursor (ties: the
    smallest unit identifier) among the sets this run has not failed on,
    using the cursors this run has already advanced.
    """
```

`max_steps` is validated like `slice_seconds` (a positive integer that is not a `bool`; otherwise `ValueError(f"max_steps must be a positive integer, got {max_steps!r}")`); add `_require_steps` beside `_require_slice`.

The prelude (wilderness, provisioning, cursor attribute, `now`, `cursors`, `pending`) and its world-fault handler are unchanged, except that every early `return False` becomes `return 0`.

The loop:

```python
    candidates = [[cursor, units] for cursor, units in pending]
    advanced: dict[str, int] = {}
    settled = failed = 0
    while candidates and settled < max_steps and failed < MAX_FAILED_SETS_PER_RUN:
        position = min(
            range(len(candidates)),
            key=lambda item: (candidates[item][0], min(candidates[item][1])),
        )
        start, units = candidates[position]
        target = min(now, start + slice_seconds)
        registry = None
        try:
            ...  # the present body: build_scope, snapshot, event, held registry,
            ...  # atomic, settle_population_scope, on_commit log_info
        except Exception as error:
            ...  # the present handler: restore, log_error
            del candidates[position]
            failed += 1
            continue
        settled += 1
        for unit_id in units:
            advanced[unit_id] = target
        if target >= now:
            del candidates[position]
        else:
            candidates[position][0] = target
    return settled
```

- The `remaining` count of the event: `_units_still_lagging(pending, cursors, advanced, units, target, now)`, where a unit's tick after this step is the largest of its recorded cursor, `advanced.get(unit_id, 0)`, and `target` when the unit is in `units`. Change the helper's parameters accordingly; it stays a pure function.
- After a successful step the set's lowest cursor is exactly `target`: the step started from the lowest cursor `start < target`, and a settlement never lowers a cursor.

Why re-selecting from in-memory cursors is sound: a scoped pass writes only inside its own closed set, so no other candidate's units, groups or cursors change. The candidate itself may have split (a linking group arrived) or gained groups (births); a later step seeds `build_scope` with the same unit set, and the closure of a union of closed sets is closed, so the pass is still lawful and every unit still starts from its own cursor. A run of `n` steps therefore does what `n` consecutive runs of one step did before.

Why a step count and not "settle the whole lag": the slice bounds one transaction and one rollback registry; the step count bounds one reactor block. Both are counts a test can assert.

Alternative rejected: one longer pass per set (several slices in one transaction). It would save the per-step fixed work, but it makes one transaction, one rollback registry and one reactor block grow with the lag of the most neglected set, which is the unbounded step the drain exists to avoid. A longer slice is available through `POPULATION_DRAIN_SLICE_SECONDS` without code.

### D2. The periodic caller and the setting

`PopulationDrainScript.at_repeat`, last line:

```python
        drain_population_backlog(
            settings.POPULATION_DRAIN_SLICE_SECONDS,
            settings.POPULATION_DRAIN_STEPS_PER_RUN,
        )
```

`server/conf/settings.py`, after the `POPULATION_DRAIN_IDLE_SECONDS` line:

```python
POPULATION_DRAIN_STEPS_PER_RUN = _env_int("POPULATION_DRAIN_STEPS_PER_RUN", 4)
```

Mirror the name in every place `POPULATION_DRAIN_IDLE_SECONDS` appears in `server/conf/test_settings.py`, `.env.example` (comment: "Settlement steps one repeat may perform; each step settles one closed set by one slice. Type: positive integer. Default: 4.") and `server/conf/tests/test_env_overrides/_support.py` (defaults map `"4"`; override case `("POPULATION_DRAIN_STEPS_PER_RUN", "POPULATION_DRAIN_STEPS_PER_RUN", "2", "2")`; invalid value `("POPULATION_DRAIN_STEPS_PER_RUN", "0", "expected a positive integer")`; name map; environment filter tuple).

Update the module docstring, `__all__` (`MAX_FAILED_SETS_PER_RUN` replaces `MAX_SETS_PER_RUN`) and the class docstring.

### D3. One group-units computation per record

In `world/maps/population_units.py`:

```python
#: Every group's units for one activity record, pinned to the unit index, the
#: published geography and the record itself. The record is immutable and every
#: write replaces it, so its identity proves the answer current.
_GROUP_UNITS = SourceMemo()
_GROUP_UNITS_KEY = "group-units"


def group_units_map(index: UnitIndex, state: Any) -> Mapping[str, frozenset[str]]:
    """Every group's units, computed once per unchanged settlement record."""
    from world.maps.geography import current as current_geography

    return _GROUP_UNITS.resolve(
        (index, current_geography(), state),
        _GROUP_UNITS_KEY,
        lambda: MappingProxyType(
            {
                group_id: group_units(
                    index, group, state.journeys.get(group.journey_id)
                )
                for group_id, group in state.groups.items()
            }
        ),
    )
```

- `SourceMemo.resolve` drops its value whenever any source object differs, so the memo holds one record's answer at a time and never grows.
- The return type becomes a read-only `Mapping`. The callers (`_closure_over`, `closed_sets`, `build_scope`, `unit_closure`) only read it; change the annotations of `_closure_over`'s parameter and local names where they say `dict`.
- `warm_group_units` keeps its body; it now also fills this memo for the record read at startup.
- `state.journeys.get(None)` for a group with no journey answers `None`, as the present comprehension relies on.

Alternative rejected: passing a prebuilt scope into `settle_population_scope`. With the memo the second `build_scope` costs a closure over already computed sets, and every entry point keeps its signature.

Not needed: sharing one activity read between `lagging_sets` and `build_scope`. `read_monster_activity` already answers the same object for an unchanged record; the separate reads cost one identity comparison each.

### D4. Candidates assessed and not proposed

- **Fewer SQL statements per step as its own work item.** The activity record's share is removed by `monster-activity-record-parts`. The rest of a step's statements store per-individual physiology (gauges, fatigue, sleep receipts) through the deferred attribute buffer, one store per changed attribute: that is the settlement's outcome, not overhead. No further reduction can be named from the code without a statement-level profile of the merged result; task 4.2 records one.
- **A drain that keeps up with an active player.** Not achievable by scheduling. Every group decides every 60 to 600 game seconds and a player action advances the clock by hundreds of game seconds, so one action creates decision work for every group of the world, and all of it runs on the one reactor thread the player's next command needs. The design answer stays what it is: unobserved units lag and are settled when idle or when needed. This batch makes each idle second pay more.
- **A background thread or process.** Excluded by the request and by the module's own invariants.

### D5. Documentation

- `docs/development/regional-monster-population.md`, drain section: rewrite step 4 of "One run" as the step loop of D1 (selection from updated cursors, one slice per step, the stop conditions); in "Failure" replace "tries the next most lagging set" with the D1 rule (a failed set is not retried in the same run; three failed sets end the run); in "The event" say one event per settled step; in "The periodic caller" add the setting row (`POPULATION_DRAIN_STEPS_PER_RUN` | `4` | Settlement steps one repeat may perform) and note the function's `int` result; the by-hand loop `while drain_population_backlog(600): pass` stays valid and may pass a larger `max_steps`. Add one paragraph "Shared group units" describing D3.
- `docs/development/settings-and-environment.md`: one row after `POPULATION_DRAIN_IDLE_SECONDS`, in zh-TW like its neighbours.
- `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2, the `population_backlog_drained` and `population_backlog_drain_failed` rows: say one info event per settled step, and that a failed set is skipped for the rest of the run.

## Risks / Trade-offs

- [A run blocks the reactor for up to four steps instead of one] → The run only starts inside the idle window of `population-drain-idle-gate`, and the step count is one environment variable. Task 4.2 records the measured time of one run; it is information, not a gate.
- [A stale group-units answer after a write that kept the record object] → Not possible: the record is immutable and every write replaces it; the memo is keyed on the record object, the index object and the geography object.
- [A caller mutated the returned mapping] → The mapping is a `MappingProxyType`; a mutation raises.

## Open Questions

- The default of 4 steps is a starting value, tunable through the environment without a code change.
