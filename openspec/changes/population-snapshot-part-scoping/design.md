# Design

## Context

See `proposal.md` for the motivation. This design builds on `monster-activity-record-parts` (called "the parts change" below): its design D1 (header and parts), D2 (placement), D3 (`_ASSEMBLED`, `read_stored_monster_activity`) and D6 (`activity_record_surfaces`).

Current code after the parts change:

- `monster_activity.activity_record_surfaces(wilderness)` answers the header entry plus one entry per listed part and per unit of the current index.
- `monster_activity.snapshot_activity_surfaces(wilderness, *, member_ids=None)` puts those entries on the wilderness surface (nothing while a batch is active) and adds one surface per individual. `member_ids` narrows the individuals only.
- `monster_activity.snapshot_monster_activity_surfaces(start_tick, end_tick, *, scope=None)` calls it with `member_ids=_scoped_individual_ids(state, scope)` when a scope is given.
- `regional_population.snapshot_population_surfaces(wilderness)` merges the same activity entries into the population surfaces; `snapshot_regional_population_surfaces(start_tick, end_tick)` calls it.
- `population_lifecycle.snapshot_population_lifecycle_surfaces(start_tick, end_tick, *, scope=None)` derives the observed scope when none is given, then merges the site, regional and activity registries by object identity. The clock advance, `ensure_population_current` and `drain_population_backlog` all build their registry through it.
- `PopulationScope` (`world/maps/population_units.py`) carries `units` and `group_ids`. A scoped pass may write only the groups of `group_ids` and the groups it creates; `create_group` refuses a group whose units are not all inside the scope, and a group's home unit is one of its units.
- `retire_settled_decision_receipts` lets a scope consume a receipt whose group no longer exists only when the scope holds `RESIDUAL_UNIT`.

## Goals / Non-Goals

**Goals:**

- The registry of a scoped settlement names only the activity parts that settlement can write.
- Each activity part is copied once per registry.

**Non-Goals:**

- No narrowing for callers that pass no scope. `snapshot_activity_surfaces(wilderness, member_ids=...)` used by single-group operations, and `snapshot_population_surfaces(wilderness)` used by registration, bootstrap, GM tools, the quest materializer and movement settlement, keep the whole record. Narrowing those needs a per-operation proof of which parts each can write and is not part of this change.
- No change to the other population records in the registry (`regional_population`, `population_timeline`, `itemcoordinates`, the zone scope, the seed, the unit cursors): they stay whole.
- No change to any restore function, to the stored format, or to `PopulationScope`.

## Decisions

### D1. `activity_record_surfaces` takes the units to name

```python
def activity_record_surfaces(
    wilderness: Any, *, units: Iterable[str] | None = None
) -> dict[tuple[str, str | None], tuple[bool, Any]]:
```

- `units is None`: unchanged (header, every listed part, every unit of the current index).
- Otherwise: the header entry plus one part entry for each unit of `units`, and nothing else. A unit with no stored part answers `(False, None)` as before. `units=()` answers the header entry alone.

### D2. `scope_part_units`

New public function in `world/maps/monster_activity.py`:

```python
def scope_part_units(wilderness: Any, scope: Any) -> frozenset[str]:
    """Every unit whose part a pass of ``scope`` may write.

    The scope's own units (a group the pass creates is placed in its home
    unit, which lies inside the scope), the part holding each group of the
    scope (a group stays in the part it was first stored in), and -- only when
    the scope holds the residual unit -- each part storing a receipt whose
    group no longer exists.
    """
```

Implementation: `state = read_stored_monster_activity(wilderness)`, then read the placement map of `_ASSEMBLED`.

1. Start with `set(scope.units)`.
2. For each `group_id` of `scope.group_ids`, add `placement.get(("g", group_id))` when it is not `None`.
3. When `population_units.RESIDUAL_UNIT in scope.units` (import `population_units` inside the function): for each `operation_id, receipt` of `state.receipts` with `receipt.group_id not in state.groups`, add `placement[("r", operation_id)]`.

Journeys and receipts of a living group need no rule of their own: the parts change places both in their group's part when they are created, and entries never move.

A malformed record raises `MonsterActivityError` from the read; the callers of D3 handle it.

### D3. The activity owner's scoped snapshot

`snapshot_activity_surfaces` gains one keyword:

```python
def snapshot_activity_surfaces(
    wilderness: Any,
    *,
    member_ids: Iterable[int] | None = None,
    units: Iterable[str] | None = None,
) -> dict[int, SurfaceSnapshot]:
```

It passes `units` to `activity_record_surfaces(wilderness, units=units)`. `units=None` is today's behaviour, so no existing caller changes.

`snapshot_monster_activity_surfaces(start_tick, end_tick, *, scope=None)`:

- `scope is None`: unchanged.
- With a scope: `snapshot_activity_surfaces(wilderness, member_ids=_scoped_individual_ids(state, scope), units=scope_part_units(wilderness, scope))`.
- The existing `except MonsterActivityError` branch (a malformed record) becomes `snapshot_activity_surfaces(wilderness, member_ids=(), units=None)`: a record that cannot be read is snapshotted whole, as today.

### D4. The regional owner stops copying the activity parts for a scoped registry

```python
def snapshot_population_surfaces(
    wilderness: Any, *, activity_units: Iterable[str] | None = None
) -> dict[int, SurfaceSnapshot]:

def snapshot_regional_population_surfaces(
    start_tick: int, end_tick: int, *, activity_units: Iterable[str] | None = None
) -> dict[int, SurfaceSnapshot]:
```

`snapshot_population_surfaces` passes `activity_units` to `monster_activity.activity_record_surfaces(wilderness, units=activity_units)`; `snapshot_regional_population_surfaces` forwards its keyword. `None` is today's behaviour for every existing caller.

In `population_lifecycle.snapshot_population_lifecycle_surfaces`, after the scope has been derived, call the regional registry as:

```python
regional_population.snapshot_regional_population_surfaces(
    start_tick, end_tick, activity_units=None if scope is None else ()
)
```

With a scope, the regional registry contributes the header only and the activity owner's registry (D3) contributes the scoped parts; the merge by object identity unites them. Put a one-line comment at this call saying exactly that. `activity_units` is a merge-only parameter: a registry built with `activity_units=()` and restored without the activity owner's registry would restore the header without its parts. Say so in both docstrings; no other caller may pass it. With no scope (no wilderness or an unprovisioned world) nothing changes.

The clock registers this function as the stage's `surfaces` contract with the signature `(start_tick, end_tick)`; that signature does not change.

### D5. Documentation

In `docs/development/regional-monster-population.md`, section "Activity record storage", add a subsection "Scoped snapshots": the three rules of D2, the statement that unscoped callers keep the whole record, and the list of the three scoped callers (clock advance, catch-up, drain).

## Risks / Trade-offs

- [A scoped pass writes a part the registry did not name, and a failure then leaves that part ahead of the database] → The three rules of D2 follow the writers' own guards: a scoped pass settles only `scope.group_ids` and groups it creates (`settling_group_ids`), creation is refused outside the scope's units (`require_units_in_active_scope`), and an orphan receipt is consumed only under the residual unit. Task 2.2 adds a test that runs real scoped passes and compares the parts they stored against `scope_part_units`.
- [The scope the registry was built for differs from the scope the stage later builds, because an earlier stage of the same advance wrote the activity record] → The same exposure the registry's individual surfaces already have; `snapshot_population_lifecycle_surfaces` documents why the two scopes name the same set. Not widened by this change.
- [A write-time guard that refuses a part outside the named set was considered] → Not added: the batched record is stored when `batched_state_writes` exits, after `population_units.scoped` has already exited in `_run_pass`, so the guard would need the pass's context order changed. The writers' existing scope guards and test (d) of task 2.2 cover the rule.
- [The remaining whole records in the registry (`itemcoordinates`, the timeline, the zone records) still cost a full copy] → Out of scope; task 3.2 records their share so a later change can be justified with a measurement.

## Migration Plan

None. No stored format changes.
