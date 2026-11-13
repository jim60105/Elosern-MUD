# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49` (re-locate by symbol name):

- Evennia 6.1.0 `Attribute.value` setter is exactly `self.db_value = to_pickle(new_value); self.save(update_fields=["db_value"])`. The getter is `from_pickle(self.db_value, db_obj=self)` with no other cache. `obj.db.name = value` and `obj.attributes.add(name, value)` reach that setter when the Attribute row exists.
- Therefore assigning `attribute.db_value = to_pickle(value)` without `save()` makes every ordinary reader (`obj.db.name`, `attributes.get`, the identity-keyed decodes) see the new value, while the database row is unchanged.
- Write sites inside a pass:
  - `regional_population._write_timeline` (`wilderness.db.population_timeline = ...`), called per body by `record_population_transition` and by `settle_timeline_through`;
  - `regional_population._write_state` (`wilderness.db.regional_population = ...`);
  - `wilderness.db.itemcoordinates = ...` in `monster_activity._begin_group_journey`, `monster_activity._arrive` and `regional_population._commit_planned_wave`;
  - `monster_sites._write_state` and the coordinate writes in `world/maps/monster_sites.py` (find them with `grep -n "_ITEMCOORDINATES_ATTRIBUTE\|itemcoordinates" world/maps/monster_sites.py`);
  - `fatigue.write_fatigue_state` (two `attributes.add` calls);
  - `clock._settle_gauge_regen`: `gauge.current = ...` and `gauge.regen_remainder = ...`, each of which saves the whole trait record through Evennia's saver dictionary.
- `settlement-outer-rollback` provides `world.rules.surfaces.outer_rollback_owner`, `suspended_outer_rollback`, `outer_rollback_active`, opened by `population_lifecycle.settle_population_lifecycle` only inside `WorldClock.advance`.
- `settlement-decode-reuse` provides `regional_population._DECODED_TIMELINE`, `_DECODED_ZONE_MAP`, `_DECODED_ZONE_STATES`, keyed on the stored `db_value` object.
- `world.rules.clock._refresh_advance_entity_caches` shows the supported way to re-point a `TraitHandler` at a replaced trait record: assign `entity.traits.trait_data` from `attributes.get("traits", category="traits")` and clear `entity.traits._cache`.

## Goals / Non-Goals

**Goals:**

- One deferral buffer, open exactly while the outer rollback owner is active.
- Transparent to readers: no read site changes.

**Non-Goals:**

- No deferral of sleep receipts, buffs, object `location`, object creation or deletion.
- No change to `monster_activity.batched_state_writes` or to the activity record.
- No accumulation of gauge seconds across settlement calls and no caching of `evaluate_combat_modifiers`.
- No patching or subclassing of Evennia classes.
- No deferral outside a clock advance.

## Decisions

### D1. Deferred attribute store in `world/rules/surfaces.py`

```python
@dataclass(slots=True)
class _DeferredStores:
    pending: dict[int, tuple[Any, Any]] = field(default_factory=dict)  # id(attribute) -> (attribute, original db_value)


_DEFERRED: _DeferredStores | None = None


@contextmanager
def deferred_attribute_stores() -> Iterator[None]:
    """Buffer stores; flush once on normal exit; on an exception put originals back and store nothing."""


@contextmanager
def flushed_attribute_stores() -> Iterator[None]:
    """Flush now, run the enclosed work unbuffered, then resume buffering."""


def store_attribute(obj: Any, key: str, value: Any, category: str | None = None) -> None:
    """Write one attribute value, deferring the database store when a buffer is open."""
```

`store_attribute`:

1. If `_DEFERRED is None`: `obj.attributes.add(key, value, category=category)` and return.
2. `attribute = obj.attributes.get(key, category=category, return_obj=True)`. If it is `None` (the row does not exist yet): `obj.attributes.add(...)` and return.
3. If `id(attribute)` is not in `pending`, record `(attribute, attribute.db_value)`.
4. `attribute.db_value = to_pickle(value)` with `from evennia.utils.dbserialize import to_pickle`.

Flush: for each pending attribute in insertion order call `attribute.save(update_fields=["db_value"])`, then clear `pending`. Discard (exception path): for each pending attribute in reverse insertion order assign `attribute.db_value = original`, then clear `pending`; store nothing. A nested `deferred_attribute_stores()` reuses the open buffer and neither flushes nor discards.

### D2. The pass opens the buffer

In `population_lifecycle.settle_population_lifecycle`, add `deferred_attribute_stores() if advance_registry_held() else nullcontext()` to the pass's `with` block, listed after `outer_rollback_owner()` so that it exits first (its flush runs while the owner scope and the activity batch are still open). In `_settle_population_at`, add `flushed_attribute_stores()` to the contact block's `with` statement, listed first.

### D3. Write sites

Replace the assignment at each site with `store_attribute`:

- `regional_population._write_timeline`: `store_attribute(wilderness, POPULATION_TIMELINE_ATTRIBUTE, {...same mapping...})`.
- `regional_population._write_state`: `store_attribute(wilderness, REGIONAL_POPULATION_ATTRIBUTE, {...})`.
- The three `wilderness.db.itemcoordinates = X` sites named in Context: `store_attribute(wilderness, ITEMCOORDINATES_ATTRIBUTE, X)` (`monster_activity.py` imports the name from `regional_population`).
- `monster_sites._write_state` and the coordinate writes of `world/maps/monster_sites.py`, with that module's `_SITES_ATTRIBUTE` and `_ITEMCOORDINATES_ATTRIBUTE`.
- `fatigue.write_fatigue_state`: both `attributes.add` calls become `store_attribute(entity, RESERVE_ATTRIBUTE, ...)` and `store_attribute(entity, POSTURE_ATTRIBUTE, ...)`. `write_fatigue_state` receives arbitrary entities; when `entity` has no `attributes.get(..., return_obj=True)` support (a pure attribute double in a test), step 2 of D1 must fall back to `attributes.add`: implement that fallback with `try/except TypeError` around the `return_obj` read and an `# observability: ignore R2:` reason comment.

Do not change any read.

### D4. Writers seed the decode reuse

After `store_attribute` in `_write_timeline`, set `_DECODED_TIMELINE = (stored.db_value, timeline)` where `stored = wilderness.attributes.get(POPULATION_TIMELINE_ATTRIBUTE, return_obj=True)` and `timeline` is the `PopulationTimeline` argument. In `_write_state`, clear `_DECODED_ZONE_MAP` and `_DECODED_ZONE_STATES` to `None` (the writer receives raw mappings, so there is nothing decoded to seed). Skip the seeding when `stored is None`.

### D5. One trait store per body in `clock._settle_gauge_regen`

Keep the function's decisions and arithmetic unchanged. Collect, per entity, the list of `(key, new_current, new_remainder)` instead of assigning inside the loop. Then:

- If `world.rules.surfaces._DEFERRED is None` (expose it through a function `attribute_stores_deferred() -> bool`), assign `gauge.current` and `gauge.regen_remainder` exactly as today.
- Otherwise build the new record once: `record = deserialize(entity.attributes.get("traits", category="traits"))` with `from evennia.utils.dbserialize import deserialize`; for each collected gauge set `record[key]["current"] = round(min(max(new_current, gauge.min), gauge.max))` and `record[key]["regen_remainder"] = new_remainder`; `store_attribute(entity, "traits", record, category="traits")`; then re-point the handler as `_refresh_advance_entity_caches` does (`entity.traits.trait_data = entity.attributes.get("traits", default={}, category="traits")`; `entity.traits._cache.clear()`).

Before writing this branch, the worker confirms in a shell that the trait record's gauge entry really holds the keys `current` and `regen_remainder` for a regenerated synthetic monster (`dict(entity.attributes.get("traits", category="traits")["hp"])`). If the key names differ, use the observed names; if the record shape is not a mapping of gauge key to mapping, stop and report.

An entity without `attributes` (a test double) takes the first branch.

### D6. Tests

New `world/maps/tests/test_settlement_deferred_writes.py`, on `ActivityFixture`, using `settlement_projection`, `self._register_lifecycle()` and `get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])`.

- Pure buffer tests against a throwaway object created with `evennia.utils.create.create_object`: deferred value is readable and not stored (re-read through `Attribute.objects.get(pk=...).db_value` shows the old value); flush stores once; an exception restores the original in memory and stores nothing; `flushed_attribute_stores` stores then resumes; a missing row falls back to `attributes.add`; nesting reuses the buffer.
- "Statements do not grow with boundary ticks": `CaptureQueriesContext(connection)`; count statements whose SQL starts with `UPDATE "typeclasses_attribute"` and ends with the row id of the timeline attribute, of the coordinate attribute and of each member's reserve attribute (ids read through `attributes.get(..., return_obj=True).pk`).
- "Readers see pending values": patch `monster_activity._arrive` or use a `side_effect` wrapper on `regional_population.settle_timeline_through` to inspect `wilderness.db.itemcoordinates`, `read_population_timeline` and `presence_at` mid-pass.
- "Contact sees stored state": wrap `world.rules.field_contact.settle_population_contact_at` as imported in `_settle_population_at` and assert `world.rules.surfaces._DEFERRED is None` and that the pending rows already equal their in-memory values in the database.
- "Results are unchanged": `run(parts, deferred)`; `deferred=False` patches `world.maps.population_lifecycle.deferred_attribute_stores` with `contextlib.nullcontext`. Bodies of the travelling group are built with gauges below maximum (the fixture's `_group` accepts body setup; otherwise lower `traits.hp.current` after creation). Compare projections in memory, then call `attributes.reset_cache()` on the wilderness and every body, re-point each `traits` handler, and compare again.
- "Fault after deferred writes": a `side_effect` wrapper on `monster_activity.settle_group_decisions_at` raises on its third call.
- "Three regenerating gauges": count writes of the body's trait attribute row inside a pass, and compare the resulting gauges with a second identical body settled through `world.rules.clock.settle_gauge_regeneration` with no buffer open.

### D7. Documentation

Add a section "Deferred stores inside an advance" to `docs/development/monster-field-behaviour.md`: the buffer, the write sites, the contact flush, the failure behaviour, and the rule that a new pass writer of a wilderness record uses `store_attribute`.

## Risks / Trade-offs

- [Code inside the pass resets an attribute cache or flushes the idmapper while values are pending, and loses them] → no such call exists in the pass outside the contact block, which flushes first; the cache-reset comparison in "Results are unchanged" detects a lost value.
- [A raw SQL reader inside the pass sees the old row] → none exists in the pass; `server/saves` and `world/rules/npc_persona` raw reads run outside it.
- [The direct trait record write of D5 bypasses a setter side effect] → `DeterministicGaugeTrait` disables the timer and its setter only clamps and rounds; D5 applies the same clamp and round, and the last scenario compares against the per-gauge writer.
- [An in-place mutation of a saver value stores immediately and leaves the row newer than other pending rows] → harmless inside one transaction; the final flush stores the same in-memory value again.
