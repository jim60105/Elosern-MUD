# Design

## Context

See proposal.md (Why). Facts at `9b67edf2` that this design relies on:

- `world/maps/regional_population.py`
  - `_state_map(wilderness)` reads `wilderness.db.regional_population`. Evennia unpickles the stored value on every read, and the function then copies every record.
  - `zone_state(wilderness, zone_key)` calls `_state_map` and `read_population_seed`, validates one record, and returns `ZonePopulationState(zone_key, seed, sequence, due, settled)`.
  - `counts_from_presence(zone_key, presence, *, wilderness)` loads `_region_cells(_zone(zone_key))` and iterates `presence.items()`. It returns `PopulationCounts(local_ids, home_ids, cell_ids)`.
  - `note_population_boundaries(wilderness, zone_keys, *, tick)` reads presence once and `_state_map` once. It then calls `_boundary_fields(wilderness, zone_key, tick, presence)` per zone, and that call runs `zone_state` (one more decode) and `counts_from_presence` (one more full scan).
  - `settle_recovery_due(wilderness, zone_key, *, tick)` returns `[]` and writes nothing when the zone's `recovery_due_tick` is `None` or later than `tick`.
- `world/maps/population_lifecycle.py`
  - `_settle_population_at` loops `for zone_key in zone_keys: settle_recovery_due(...)` over every initialized zone.
  - `_next_population_boundary` loops every zone and calls `zone_state`.
- `world/maps/population_forecast.py`
  - `capture_activity_snapshot` builds `ProjectedZone` rows from `zone_state(wilderness, key)` for each key of `initialized_zone_keys(wilderness)`.
  - `_Projection._note_zone_boundary(tick)` calls `self._counts(key)` (a full `counts_from_presence` scan) for every zone. `run()` calls it three times per step, for up to `MAX_PROJECTION_STEPS` steps.
- `validate_ecology_geometry` already rejects two zones that share a parent-region cell, so one cell belongs to at most one zone. The index below still maps a cell to a tuple of zone keys, so its result never depends on that validation.

## Goals / Non-Goals

**Goals:** one state decode and one presence scan per boundary zone pass, with results identical to the per-zone reads.

**Non-Goals:** activity-group decision cost, provisioning cost, birth-cell memoisation (`population_geometry` already memoises cells per publication), forecast step caps, any change to persisted shapes, events, ordering or determinism, and any wall-clock assertion.

## Decisions

### D1. Batch readers in `world/maps/regional_population.py`

Add the following functions next to the existing ones, and list the three public names in the module's `__all__` if the module defines one.

```python
def _zone_state_from_record(
    zone_key: str, record: Mapping[str, object] | None, world_seed: int
) -> ZonePopulationState | None:
    """Validate one stored zone record against an already read world seed."""
```

Move the body of `zone_state` after `record = ...` into this helper unchanged: the missing-field check, the `initialized is True` check, `_require_seed`, `_require_int`, the optional due tick, and the seed-disagreement refusal. The only change is that it compares against the `world_seed` argument instead of calling `read_population_seed`. `zone_state` becomes:

```python
def zone_state(wilderness: Any, zone_key: str) -> ZonePopulationState | None:
    _require_wilderness(wilderness)
    record = _state_map(wilderness).get(zone_key)
    if record is None:
        return None
    return _zone_state_from_record(zone_key, record, read_population_seed(wilderness))
```

```python
def zone_states(wilderness: Any) -> dict[str, ZonePopulationState]:
    """Every initialized zone's validated state from one decode, in key order."""
    _require_wilderness(wilderness)
    states = _state_map(wilderness)
    if not states:
        return {}
    world_seed = read_population_seed(wilderness)
    return {
        key: _zone_state_from_record(key, states[key], world_seed)
        for key in sorted(states)
    }


def due_recovery_zone_keys(wilderness: Any, *, tick: int) -> tuple[str, ...]:
    """Zone keys whose recovery is due at or before ``tick``, in key order."""
    _require_argument_int(tick, "tick")
    return tuple(
        key
        for key, state in zone_states(wilderness).items()
        if state.recovery_due_tick is not None and state.recovery_due_tick <= tick
    )


def zone_counts_from_presence(
    zone_keys: Iterable[str],
    presence: Mapping[object, PopulationPresence],
    *,
    wilderness: str,
) -> dict[str, PopulationCounts]:
    """Every listed zone's three measures from one scan of ``presence``."""
```

The body of `zone_counts_from_presence`:

1. `keys = tuple(dict.fromkeys(zone_keys))`, which keeps first-seen order and drops repeats.
2. Build `owners: dict[tuple[int, int], tuple[str, ...]]` by iterating `keys` and, for each key, every cell of `_region_cells(_zone(key))`, appending the key to that cell's tuple.
3. Create `home = {key: set() for key in keys}` and `cells = {key: {} for key in keys}`.
4. Iterate `presence.items()` exactly once. Skip a fact that is not alive. When `fact.home_zone in home`, add the ID to that set. Skip the position step when `fact.position` is `None` or `fact.position.wilderness != wilderness`. Otherwise, for each `key` in `owners.get((x, y), ())`, run `cells[key].setdefault((x, y), set()).add(individual_id)`.
5. Return `{key: PopulationCounts(local_ids=..., home_ids=frozenset(home[key]), cell_ids=MappingProxyType(...))}`, building each value exactly as `counts_from_presence` builds it today.

`counts_from_presence(zone_key, presence, *, wilderness)` becomes `return zone_counts_from_presence((zone_key,), presence, wilderness=wilderness)[zone_key]`. Its docstring stays.

The alternative was a module-level memo keyed on presence identity. It was rejected: the presence mapping is rebuilt per pass, so identity keys would miss and an extra cache layer would need invalidation.

### D2. Note pass

Split `_boundary_fields` into a pure core and a wrapper:

```python
def _boundary_fields_from(
    state: ZonePopulationState | None,
    zone_key: str,
    tick: int,
    counts: PopulationCounts,
    lower: int,
) -> dict[str, object]:
```

The core holds today's body after the `state`, `zone`, `lower` and `counts` lookups, unchanged. It returns `{}` for `state is None` and reads `_zone(zone_key).recovery_delay`. `_boundary_fields(wilderness, zone_key, tick, presence)` keeps its signature for `note_population_boundary`. It computes `state = zone_state(...)`, returns `{}` when that is `None`, and otherwise delegates with `counts_from_presence(...)` and `density_lower_bound(wilderness, zone_key)`.

`note_population_boundaries` becomes:

```python
presence = presence_at(wilderness, at_tick=tick)
raw = _state_map(wilderness)
world_seed = read_population_seed(wilderness) if raw else None
counts = zone_counts_from_presence(keys, presence, wilderness=_wilderness_name(wilderness))
changed = False
for zone_key in keys:
    record = raw.get(zone_key)
    state = None if record is None else _zone_state_from_record(zone_key, record, world_seed)
    if state is None:
        continue
    fields = _boundary_fields_from(
        state, zone_key, tick, counts[zone_key], density_lower_bound(wilderness, zone_key)
    )
    if fields:
        raw[zone_key] = {**raw[zone_key], **fields}
        changed = True
if changed:
    _write_state(wilderness, raw)
```

Keep the early `if not keys: return` and the argument checks. `_state_map` already returns fresh dict copies, so updating `raw` in place is safe.

### D3. Lifecycle coordinator (`world/maps/population_lifecycle.py`)

- In `_settle_population_at`, replace `for zone_key in zone_keys:` (the `settle_recovery_due` loop only) with `for zone_key in regional_population.due_recovery_zone_keys(wilderness, tick=tick):`. Keep `zone_keys` for the three `_note_boundary` calls. This is equivalent: a zone that is not due returns `[]` without any write, and settling one zone writes only that zone's record, so the due set read before the loop stays exact.
- In `_next_population_boundary`, replace the loop over `_zone_keys(wilderness)` with `for state in regional_population.zone_states(wilderness).values():` and read `state.recovery_due_tick`.

### D4. Forecast (`world/maps/population_forecast.py`)

- `capture_activity_snapshot`: build `zones` from `regional_population.zone_states(wilderness).values()`, mapping each `ZonePopulationState` to `ProjectedZone` with the same five fields. Ordering stays key order.
- `_Projection._note_zone_boundary`: compute `counts = zone_counts_from_presence(sorted(self.zones), self.presence, wilderness=self.wilderness)` once, then loop `for key in sorted(self.zones)` using `len(counts[key].local_ids)`. Import `zone_counts_from_presence` from `world.maps.regional_population` inside the method, matching the existing local imports.
- `_settle_zone_recoveries` is unchanged. It already skips zones that are not due and must re-measure after each projected wave.

### D5. Tests: new `world/maps/tests/test_population_zone_pass.py`

The first docstring line is `"""Behavior tests: one boundary zone pass reads shared population facts once."""`. The module names no shipped zone, coordinate, density or count, and it is a behaviour module, so it gets no data-contract seed entry. Register it once in `.github/evennia-shards.json`, appending `"world.maps.tests.test_population_zone_pass"` to the `labels` of shard `maps-34-6` (the one holding `world.maps.tests.test_regional_population_recovery`).

Shared helper: `class CountingPresence(dict)` overrides `items(self)` to increment `self.items_calls` and return `super().items()`.

1. `ZoneCountsIndexTests(unittest.TestCase)` uses pure seams only. Patch `owner._zone` with a function returning `object()` and `owner._region_cells` with a function mapping six synthetic zone keys (`t_a` … `t_f`) to disjoint two-cell frozensets. Build a `CountingPresence` of `PopulationPresence` facts: one living individual inside each zone's first cell, one living individual whose `home_zone="t_c"` standing outside every zone, one dead individual inside `t_a`, and one living individual in another wilderness name inside `t_b`'s cell.
   - `test_one_scan_serves_every_zone`: `zone_counts_from_presence(keys, presence, wilderness="w")` leaves `items_calls == 1`, and the per-zone `local_ids`, `home_ids` and `cell_ids` equal the hand-derived sets: each zone's own inside ID, `t_c` home holding the outside ID, the dead and foreign IDs absent.
   - `test_single_zone_reader_agrees`: for every key, `counts_from_presence(key, presence, wilderness="w")` equals the batch result for that key.
2. `ZonePassDecodeTests(RegistryIsolationMixin, EvenniaTest)` follows the setup of `world/maps/tests/test_regional_population.py::RegionalPopulationTests`: `publish_shipped_map_world()`, `synthetic_registries("monster_species", "monster_variants", "monster_tiers")` and `create_wilderness`. Patch `owner.ECOLOGY_ZONE_REGISTRY` with six synthetic zones on distinct placeholder rectangles, patch `owner._region_cells` with disjoint synthetic cells, patch `owner.eligible_birth_cells` so every zone's lower bound is 1, and call `initialize_population_seed(..., seed=SEED, tick=0)`. Write the state map directly (the `_initialize_state` pattern), with all six zones initialized, settled at 0 and not due.
   - `test_note_pass_decodes_once`: with `patch.object(owner, "_state_map", wraps=owner._state_map) as decode`, call `owner.note_population_boundaries(wilderness, keys, tick=100)` with no living individuals. Assert `decode.call_count == 1`, and assert every zone record now has `recovery_due_tick == 100 + zone.recovery_delay` and `settled_through_tick == 100`. That is the result `note_population_boundary` gives for one zone; verify it by running the single-zone call on a copy of the original state in the same test.
   - `test_due_reader_decodes_once_and_filters`: set `recovery_due_tick` to 50 on `t_b` and `t_e`, to 500 on `t_c`, and to `None` on the rest. With the `_state_map` wrap, `owner.due_recovery_zone_keys(wilderness, tick=100)` returns `("t_b", "t_e")` with `decode.call_count == 1`.
   - `test_lifecycle_settles_only_due_zones`: same state, `patch.object(regional_population, "settle_recovery_due", wraps=...)` from inside `world.maps.population_lifecycle`'s namespace (`population_lifecycle.regional_population`). Call `population_lifecycle._settle_population_at(wilderness, 100)` and assert the wrapped mock's call keys, in order, are `["t_b", "t_e"]`.
3. `ForecastZoneNoteTests(unittest.TestCase)`: build `ActivitySnapshot(groups=(), journeys=(), presence=(), zones=<six ProjectedZone rows, all not due>, sites=(), protection=(), room_protection=(), physiology=(), condition_ticks=(), wilderness="w")`. Construct `_Projection(snapshot, start_tick=0, wilderness="w", observers=())`. Patch `world.maps.regional_population.zone_counts_from_presence` with a `wraps=` mock, and patch `world.maps.regional_population.zone_lower_bound` to return 1, `world.maps.regional_population._zone` and `_region_cells` as in test 1. Call `projection._note_zone_boundary(10)`. Assert one call, and assert every zone's `recovery_due_tick == 10 + ECOLOGY_ZONE_REGISTRY[key].recovery_delay` (patch `ECOLOGY_ZONE_REGISTRY` on `world.maps.regional_population` to the six synthetic zones).

The calls counted are the `_state_map` decode, `presence.items()` and the batch reader. Those counts are the work-set measure the requirement names. No assertion reads a clock or a duration.

## Risks / Trade-offs

- [`zone_states` validates every record, so a malformed record in an unrelated zone now refuses inside the recovery loop, where before it surfaced only when that zone was visited] → the lifecycle already visited every zone at each boundary through `zone_state`, so the refusal surface does not widen.
- [Behaviour drift during refactoring] → the existing suites `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_monster_activity` and the forecast users in `world.rules.tests.test_field_contact_boundaries` must stay green without edits.

## Verification

`/tmp/mud-zone-pass.env` contains `MUD_TEST_SETTINGS=1`. Run each label alone, from the repository root:

`uv run --locked --env-file=/tmp/mud-zone-pass.env evennia test --settings test_settings.py --keepdb <label>` for `world.maps.tests.test_population_zone_pass`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_monster_activity`, `world.rules.tests.test_field_contact_boundaries`. A label that discovers more than 100 tests runs one class at a time.

Then run `uv run --locked python -m tools.contract_gate --change population-zone-pass-indexing` and `openspec validate population-zone-pass-indexing --strict`.
