# Design

## Context

See proposal.md - Why. Facts verified in `world/maps/regional_population.py` (line numbers at commit `f9925e49`; re-locate by symbol name):

- `read_population_timeline` (1173) reads `wilderness.db.population_timeline`, which unpacks the stored value on every call, then rebuilds every `PopulationTransition` and `PopulationProtection`.
- `_state_map` (436) reads `wilderness.db.regional_population` the same way; `zone_states` (634) and `zone_state` (620) rebuild `ZonePopulationState` from it and read the seed.
- `_living_presence` (1401) is reused inside `reused_living_presence()` only while `presence_fingerprint` is unchanged. Every departure and arrival changes the fingerprint, and the rebuild then calls `_living_monsters()` (`Monster.objects.all_family()` plus `persisted_hp` per row) and reads `db.home_ecology_zone` and `db.site_key` of every individual.
- `_protected_cells(wilderness, at_tick=...)` (863) reads the timeline and calls `_active_session_protection` (828), which iterates every `PlayerCharacter` and reads `db.active_combat`.
- The proven pattern already in the tree: `monster_activity._DECODED_STATE` and `regional_population._UNPACKED_REGISTRATION` key a decode on the identity of `Attribute.db_value` obtained through `attributes.get(key, return_obj=True)`. Every stored write, in-place mutation and rollback restore replaces that object (`world/maps/tests/test_monster_activity.py::BulkSettlementEconomyTests.test_read_follows_every_kind_of_stored_write`).
- `forget_living_presence()` (1395) is called by `population_lifecycle._settle_population_at` after the contact block.

## Goals / Non-Goals

**Goals:**

- Identity-keyed decode reuse for the timeline and the zone record, always on.
- Pass-scoped reuse of living individuals, static individual facts, session protection and protected cells, active only inside `reused_living_presence()`.
- A shared projection helper that later changes of the chain reuse.

**Non-Goals:**

- No change to `world/maps/monster_activity.py` (its record already has both mechanisms).
- No change to `world/maps/population_forecast.py`.
- No change to snapshots, savepoints or write counts (next two changes).
- No change to `evaluate_combat_modifiers` cost, to `Evennia` serialization, or to any stored format.
- No cache that outlives a pass except the two identity-keyed decodes.

## Decisions

### D1. Identity-keyed timeline decode

Add module state `_DECODED_TIMELINE: tuple[Any, PopulationTimeline] | None = None`. In `read_population_timeline`, after `_require_wilderness`:

1. `stored = wilderness.attributes.get(POPULATION_TIMELINE_ATTRIBUTE, return_obj=True)`.
2. If `stored is not None` and `_DECODED_TIMELINE` holds `stored.db_value` (compared with `is`), return the held timeline.
3. Otherwise run the existing body unchanged (it still reads `wilderness.db.population_timeline` and raises the same `MalformedPopulationState`), and when `stored is not None` store `(stored.db_value, timeline)`.

`PopulationTimeline` and its members are frozen dataclasses holding tuples, so the shared value is read-only.

### D2. Identity-keyed zone record decode

Add `_DECODED_ZONE_MAP: tuple[Any, dict[str, dict]] | None = None`. `_state_map` returns `{key: dict(value) for key, value in held.items()}` on an identity hit, else runs its existing body and stores the validated result. Callers keep getting a private copy they may mutate.

Add `_DECODED_ZONE_STATES: tuple[Any, Any, dict[str, ZonePopulationState]] | None = None`, keyed on the `db_value` objects of `REGIONAL_POPULATION_ATTRIBUTE` and `POPULATION_SEED_ATTRIBUTE`. `zone_states` returns `dict(held)` on a hit. `zone_state` is unchanged (it keeps validating one record only).

### D3. Pass-scoped facts

Extend the existing dataclass `_PresenceReuse` with:

```python
living: tuple[Monster, ...] | None = None
facts: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)
session_protection: tuple[PopulationProtection, ...] | None = None
protected: dict[tuple[int, int], tuple[Any, frozenset[tuple[int, int]]]] = field(default_factory=dict)
```

- `_living_presence`: when a scope is open, take the individuals from `reuse.living` (fill it from `_living_monsters()` when `None`), and take `(home zone, site key)` from `reuse.facts[individual.pk]` (fill it with the existing two `_require_optional_name` reads on a miss). With no scope the function is unchanged.
- `_active_session_protection` gets a private caller `_session_protection(wilderness)` that returns `reuse.session_protection` (filling it once) when a scope is open, else calls through. `_protected_cells` uses it.
- `_protected_cells`: only for `at_tick is not None` and an open scope, key the result on `(id(wilderness), tick)` and hold it with the timeline `db_value` object it was computed from; reuse it only while that object is the stored one. The `at_tick is None` branch is unchanged.
- `forget_living_presence()` resets all four new fields and the fingerprint.

### D4. Invalidation points

Call `regional_population.forget_living_presence()`:

- at the end of `regional_population._commit_planned_wave`, after its `try` block completed without an exception and before `return`;
- in `world/maps/monster_sites.py` at the end of `_populate`, `_apply_recovery` and `_clear_boundary`;
- in `population_lifecycle._settle_population_at`, immediately before the `with monster_activity.unbatched_state_writes():` contact block (the call after the block already exists).

`forget_living_presence()` is a no-op with no open scope, so direct owner operations are unaffected.

### D5. Shared projection helper

Create `world/maps/tests/_settlement_projection.py` with one function `settlement_projection(wilderness) -> dict`. It returns only plain, comparable values and no primary key. Individuals are labelled `"<group_id>#<index in member_ids>"`; an individual in no group is labelled `"free#<n>"` in ascending primary-key order. Content:

- `activity`: `monster_activity.state_to_dict(read_monster_activity(wilderness))` with every member id replaced by its label;
- `timeline`: settled tick, transitions and protection from `read_population_timeline`, ids replaced by labels;
- `zones`: the `_state_map` result;
- `sites`: `wilderness.db.monster_sites` unpacked to plain values, member ids replaced by labels;
- `bodies`: per label: actual cell (`regional_population.actual_cell`), whether `location` is set, `current` and `regen_remainder` of each gauge in `world.rules.clock.GAUGE_KEYS`, reserve units and posture from `read_optional_fatigue_state`, the receipt state from `read_sleep_receipt`, and the sorted active physiological buff keys.

The helper reads through public owner functions and must not be imported by production code.

### D6. Tests

New `world/maps/tests/test_settlement_decode_reuse.py`, classes built on `ActivityFixture` imported from `world.maps.tests.test_monster_activity` (it provides `_group`, `_reset_activity`, `_register_lifecycle`, `_departure_seed`, synthetic registries and a wilderness).

- Decode reuse (D1, D2): wrap the two decode bodies in private functions `_timeline_from_raw` and `_zone_map_from_raw` so a test can count calls with `patch.object(..., wraps=...)`. Scenarios "Repeated reads" and "Read follows every kind of write"; model the three write kinds on `BulkSettlementEconomyTests.test_read_follows_every_kind_of_stored_write`.
- Pass facts (D3, D4): count `_living_monsters` and `_active_session_protection` with `patch.object(..., wraps=...)` during one `settle_population_lifecycle` over an interval that the fixture's decision intervals split into several boundary ticks. Assert the counts of the scenario "Quiet pass over many boundaries". For "Protected cells per tick" count the inner computation through a private function `_protected_cells_at` extracted from the `at_tick is not None` branch.
- Differential (D5): build the scenario of the requirement "Reuse leaves settlement results unchanged" from fixture helpers. A local function `run(parts, reuse)` calls `self._reset_activity(tick=100)`, rebuilds the scenario, optionally patches `population_lifecycle.regional_population.reused_living_presence` with `contextlib.nullcontext`, settles each part with `settle_population_lifecycle`, and returns `settlement_projection(self.wilderness)`. Assert equality for `(1500,)`, `(700, 800)` and `(61, 1439)`, with and without reuse. If the fixture cannot build the zone or site half of the scenario with its existing helpers, build that half with the synthetic helpers used in `world/maps/tests/test_regional_population_recovery.py` and `world/maps/tests/test_monster_sites/`; do not use shipped zones or sites.

No expected value is computed by calling the code under test in a different mode except the differential comparison itself, which is the requirement.

### D7. Documentation

Add a section "Settlement read reuse" to `docs/development/regional-monster-population.md`: the two identity-keyed decodes, the four pass-scoped facts, the invalidation points, and the test module name.

## Risks / Trade-offs

- [A new writer of liveness, home zone or site marker inside a pass forgets to call `forget_living_presence()`] → the differential test covers births, site recovery and contact; D4 lists every current writer.
- [An identity-keyed decode returns a stale value if Evennia ever mutated `db_value` in place] → the "Read follows every kind of write" scenario fails; the same assumption already guards the activity record.
- [The residual cost of `evaluate_combat_modifiers` (about 9% of the profile) is untouched] → recorded as out of scope; `settlement-deferred-body-writes` reduces how often it runs.

## Open Questions

None.
