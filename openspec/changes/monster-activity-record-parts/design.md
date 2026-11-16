# Design

## Context

See `proposal.md` for the motivation. All line references are to `world/maps/monster_activity.py` at commit `31c01be0`.

Current storage:

- `read_monster_activity` (line 903) returns the in-flight batch state inside `batched_state_writes`; otherwise it reads the `monster_activity` attribute object, and returns the memoized decode `_DECODED_STATE` when the stored value object (`stored.db_value`) is the same object as the one the memo was decoded from. Every write replaces that object, so every write forces one full `state_from_dict` on the next read.
- `_write_state` (line 934) either parks the state in the batch or does `wilderness.db.monster_activity = state_to_dict(state)`: a full encode, a full `to_pickle` copy and one pickle of the whole record. It is the only stored writer; about thirty owner operations call it with `_copy_state(state, groups=...)`, where unchanged entries keep their object identity (each writer copies the mapping and replaces single entries; every record type is a frozen dataclass).
- Rollback is generic: a `SurfaceSnapshot` lists `(key, category) -> (existed, value)`; `clock._restore_registry_attribute`, `regional_population._restore_attribute` and `monster_activity.restore_activity_surfaces` restore each entry with `attributes.add(key, value, category=category)` or `attributes.remove(key, category=category)`. About twenty-five call sites use these three functions. This change keeps that mechanism and only changes which entries the activity record contributes.
- The activity record enters a snapshot in two places: `snapshot_activity_surfaces` (line 3444, entry `(MONSTER_ACTIVITY_ATTRIBUTE, None)`, omitted while a batch is active) and `regional_population.snapshot_population_surfaces` (entry `("monster_activity", None)`).
- Evennia lower-cases and strips attribute keys and categories, and its attribute cache is not transaction-aware: an attribute row created inside a transaction that rolls back stays in the handler cache until it is removed or the cache is reset.

Constraints: the reactor is single-threaded; no migration; settlement outcomes unchanged.

## Goals / Non-Goals

**Goals:**

- A stored write costs in proportion to the parts it changed.
- A read after a write decodes only the parts that changed.
- Rollback stays correct through the existing generic restore functions, including for a part a failed operation created.

**Non-Goals:**

- No change to any owner operation, codec of a single group, journey, receipt or room protection, `MonsterActivityState`, `_copy_state`, `batched_state_writes`, `unbatched_state_writes`, or any caller of `read_monster_activity`.
- No narrowing of rollback snapshots: after this change every activity snapshot still covers the whole record (all parts). Narrowing is `population-snapshot-part-scoping`.
- No change to the per-unit cursor record (`population_unit_cursors`): it is one small mapping of integers and stays one attribute.
- No Django model, no schema migration, no new table.
- Parts are never deleted and groups never move between parts.

## Decisions

### D1. Stored layout

On the wilderness script:

| Attribute key | Category | Value |
| --- | --- | --- |
| `monster_activity` (`MONSTER_ACTIVITY_ATTRIBUTE`, unchanged) | none | the header: exactly `{"units": [...], "room_protection": [...], "settled_through_tick": int}` |
| `part_key(unit_id)` | `monster_activity_part` (`MONSTER_ACTIVITY_PART_CATEGORY`) | one part: exactly `{"unit": unit_id, "groups": {...}, "journeys": {...}, "receipts": {...}}` |

- `units` is the sorted list of every unit identifier that has a stored part. It is the authoritative list: a read loads exactly these parts.
- `room_protection` and `settled_through_tick` keep their present encoding (`_room_protection_to_dict`, integer).
- Inside a part, `groups`, `journeys` and `receipts` use the present per-entry encodings (`group_to_dict`, `journey_to_dict`, `_receipt_to_dict`), with keys in sorted order.
- `part_key(unit_id)` is `"p" + hashlib.sha256(unit_id.encode("utf-8")).hexdigest()[:40]`. A hash is used because Evennia lower-cases attribute keys, and a unit identifier is built from authored keys whose case this module does not control. The real identifier is the part's `unit` field.

Why per settlement unit and not per group: a per-group row would be created and deleted during ordinary settlement (births, releases), and a row created in a rolled-back transaction stays in Evennia's attribute cache. A snapshot can name the parts of the units an operation may write before the operation runs (D6); it cannot name the groups an operation will create. Why not a fixed number of hash buckets: an operation would then touch buckets unrelated to its units, and the next change could not narrow a snapshot to a scope.

Why keep the header under the existing key: `activity_provisioned`, `regional_population.require_initialized_population` and the tests that remove the attribute keep working unchanged.

### D2. Placement

Every stored entry has one part, recorded in memory as `placement[(kind, id)] = unit_id` with `kind` one of `"g"`, `"j"`, `"r"`:

- A group already stored stays in its recorded part, even when its home is rewritten.
- A new group goes to `population_units.unit_of_location(population_units.current_unit_index(), group.home)` (import `population_units` inside the function, as `create_group` already does). `home` is never `None`, so the answer is always a unit identifier; a room home is the residual unit.
- A new journey goes to the part of the group named by `journey.group_id`.
- A new receipt goes to the part of the group named by `receipt.group_id` when that group is in the state being written; otherwise to `population_units.RESIDUAL_UNIT`.
- An entry that already has a recorded part never moves.

### D3. Read: assembly and the identity rule

Replace `_DECODED_STATE` with:

```python
@dataclass(frozen=True, slots=True)
class _Part:
    """The decoded entries of one stored part."""

    groups: Mapping[str, MonsterGroup]
    journeys: Mapping[str, MonsterJourney]
    receipts: Mapping[str, ActivityReceipt]


@dataclass(frozen=True, slots=True)
class _Assembled:
    """The last assembled record and the stored objects it came from."""

    header_raw: Any
    state: MonsterActivityState
    placement: Mapping[tuple[str, str], str]
    #: unit id -> (stored part value object, its decode)
    parts: Mapping[str, tuple[Any, _Part]]


_ASSEMBLED: _Assembled | None = None
```

`read_monster_activity(wilderness)`:

1. `_require_wilderness`; return the batch state exactly as today.
2. `stored = wilderness.attributes.get(MONSTER_ACTIVITY_ATTRIBUTE, return_obj=True)`; `raw = None if stored is None else stored.db_value`; `raw is None` raises `_invalid("'monster_activity' is missing from this provisioned world")` as today.
3. If `_ASSEMBLED is not None and _ASSEMBLED.header_raw is raw`, return `_ASSEMBLED.state`.
4. Otherwise `_ASSEMBLED = _assemble(wilderness, raw)` and return its state.

The identity rule: **every stored change to any part is accompanied by a new header value object.** `_store_state` (D4) always stores the header when it stores anything; a generic restore re-adds the header because every activity snapshot contains it (D6); an attribute cache reset reloads it. So one identity comparison on the header proves the whole assembled record current, exactly as the single comparison did before.

`_assemble(wilderness, header_raw) -> _Assembled`:

1. `header = _require_keys(header_raw, _HEADER_FIELDS, "monster_activity")` with `_HEADER_FIELDS = frozenset({"units", "room_protection", "settled_through_tick"})`. `units` must be a sequence of distinct nonempty strings (`_is_sequence`, `_require_name`); otherwise `_invalid`.
2. For each unit in `units` order: `stored = wilderness.attributes.get(part_key(unit), category=MONSTER_ACTIVITY_PART_CATEGORY, return_obj=True)`; a missing attribute or a `None` value raises `_invalid(f"the part of unit {unit!r} is missing")`. Reuse the previous decode when `_ASSEMBLED.parts.get(unit)` holds the same stored value object; otherwise `_part_from_dict(unit, raw)`.
3. `_part_from_dict(unit, raw)`: `_require_keys(raw, _PART_FIELDS, ...)` with `_PART_FIELDS = frozenset({"unit", "groups", "journeys", "receipts"})`; `raw["unit"] != unit` raises `_invalid`; the three values must be mappings; decode with `group_from_dict`, `journey_from_dict`, `_receipt_from_dict`; a key that differs from its decoded identifier raises `_invalid` (the checks `state_from_dict` makes today).
4. Merge the parts into three dicts and the placement map. An identifier already present from another part raises `_invalid(f"{key!r} is stored in more than one part")`.
5. Run the record-level cross-checks on the merged groups and journeys. Move the four check loops of `state_from_dict` (journey names a missing group, group does not name the journey, members differ, travelling group still positioned; group names a missing journey; member mode checks; member in two groups) into a new function `_cross_check(groups, journeys)` and call it from both `state_from_dict` and `_assemble`. `state_from_dict` keeps its signature and behaviour.
6. Decode `room_protection` and `settled_through_tick` as `state_from_dict` does. Build `MonsterActivityState` with `MappingProxyType` mappings.

New public reader:

```python
def read_stored_monster_activity(wilderness: Any) -> MonsterActivityState:
    """The stored record, ignoring any in-flight batched state."""
```

It performs steps 2 to 4 of `read_monster_activity` (no batch check).

### D4. Write: store only changed parts

`_write_state(wilderness, state)` keeps its batch branch. Its stored branch becomes `_store_state(wilderness, state)`:

1. `previous`: when the header attribute does not exist, an empty baseline (no entries, no placement, no parts, `units = ()`). Otherwise the assembled record of `read_stored_monster_activity` (taken from `_ASSEMBLED` after that call).
2. If `state is previous.state`, return (nothing changed).
3. `placement = dict(previous.placement)`, `dirty: set[str] = set()`. For each kind in the order groups, journeys, receipts:
   - for each `key, value` of the new mapping: `old = previous mapping.get(key)`; skip when `old is value or old == value`; otherwise `unit = placement.get((kind, key))`, or the D2 rule for a new entry; record it in `placement`; add it to `dirty`.
   - for each key of the previous mapping that the new mapping lacks: `dirty.add(placement.pop((kind, key)))`.
4. `units = sorted(set(previous units) | set(placement.values()))`.
5. If `dirty` is empty and `state.room_protection == previous.state.room_protection` and `state.settled_through_tick == previous.state.settled_through_tick`, return.
6. For each unit of `sorted(dirty)`: build the part mapping from the entries of the new state whose placement is that unit (group the placement map by unit once, not once per part) and call `_store_part(wilderness, unit, mapping)`.
7. Store the header: `wilderness.attributes.add(MONSTER_ACTIVITY_ATTRIBUTE, {"units": units, "room_protection": [...], "settled_through_tick": ...})`.
8. Replace `_ASSEMBLED`: the new header's stored value object (read it back with `attributes.get(..., return_obj=True).db_value`), `state`, the new placement, and for each part the stored value object and a `_Part` built from the new state (unchanged parts keep their previous tuple).

```python
def _store_part(wilderness: Any, unit: str, mapping: Mapping[str, Any]) -> None:
    """Store one part. The one function a test counts."""
    wilderness.attributes.add(
        part_key(unit), dict(mapping), category=MONSTER_ACTIVITY_PART_CATEGORY
    )
```

A part that becomes empty is stored empty and stays listed. Parts are never removed by a write.

`initialize_monster_activity` is unchanged in text: its `_write_state` of an empty state stores a header with `units == []` through the empty baseline of step 1.

New public writer for tools and tests:

```python
def write_monster_activity(wilderness: Any, state: MonsterActivityState) -> None:
    """Store ``state`` as the complete record (parks it in an active batch)."""
```

It raises `TypeError` for a value that is not a `MonsterActivityState` and calls `_write_state`.

The equality fallback (`old == value`) in step 3 keeps a writer that rebuilds an equal entry from rewriting its part. Identity is tested first, so unchanged entries cost one comparison.

### D5. `state_to_dict` and `state_from_dict`

Both keep their present whole-record mapping. They are no longer the stored form; they stay the canonical projection that tests and `world/maps/tests/_settlement_projection.py` compare. Update both docstrings to say so.

### D6. Rollback surfaces

New public function:

```python
def activity_record_surfaces(
    wilderness: Any,
) -> dict[tuple[str, str | None], tuple[bool, Any]]:
    """The header and every part as rollback surface entries.

    One entry for the header, one for each part the header lists, and one for
    each unit of the current settlement-unit index, so a part the operation
    creates is named before it exists. An entry of a part that is not stored is
    ``(False, None)``: restoring it removes the part.
    """
```

- Header entry: `(MONSTER_ACTIVITY_ATTRIBUTE, None): _db_safe_attribute_snapshot(wilderness, MONSTER_ACTIVITY_ATTRIBUTE)`.
- Units: the header's `units` (read the stored header value directly; a header that is missing or not a mapping with a sequence `units` contributes no unit) united with `population_units.all_units(population_units.current_unit_index())` (import inside the function).
- Part entry: `(part_key(unit), MONSTER_ACTIVITY_PART_CATEGORY): _db_safe_attribute_snapshot(wilderness, part_key(unit), MONSTER_ACTIVITY_PART_CATEGORY)`. `db_safe_attribute_snapshot` already answers `(False, None)` for an attribute that does not exist.

Use it in both places:

- `snapshot_activity_surfaces`: replace the one-entry mapping with `activity_record_surfaces(wilderness)`; the `_ACTIVE_BATCH is not None` case still contributes `{}`.
- `regional_population.snapshot_population_surfaces`: remove the `("monster_activity", None)` entry and merge `monster_activity.activity_record_surfaces(wilderness)` into the attribute mapping (import `monster_activity` inside the function; the module already does that in `require_initialized_population`). Update the comment.

Why this is enough for restore: the existing restore functions re-add an entry that existed and remove an entry that did not. Removing the entry of a part a failed operation created evicts it from the attribute cache, and the header entry restores the unit list without it. Re-adding the header gives it a new stored value object, so the next read assembles again (D3).

Every unit a new group can be placed in is a unit of the current index or the residual unit, and `all_units` includes both, so no created part can be missing from a snapshot.

### D7. Documentation

- `docs/development/regional-monster-population.md`: add a section "Activity record storage" before the drain section: the table of D1, the placement rule of D2, the identity rule of D3, the changed-parts rule of D4, and the rollback rule of D6. State that `state_to_dict` is the comparison projection, not the stored form.
- `docs/development/monster-field-behaviour.md`, the sentence naming "the sole `wilderness.db.monster_activity` writer": change it to say the owner is the sole writer of the activity header and parts.

### D8. Tests that touch the stored record directly

Find them with `grep -rn "db\.monster_activity\|\"monster_activity\"\|MONSTER_ACTIVITY_ATTRIBUTE" --include="*.py" world server web commands typeclasses` and apply these rules; nothing else in those tests changes:

| Pattern | Replacement |
| --- | --- |
| `wilderness.db.monster_activity = state_to_dict(X)` (`test_monster_activity.py`, `test_population_drain.py`, `test_population_units.py`, `test_settlement_outer_rollback.py`) | `monster_activity.write_monster_activity(wilderness, X)` |
| `dict(wilderness.db.monster_activity)` or `dict(wilderness.db.monster_activity or {})` used as a before/after value (`test_site_population.py`, `test_regional_population.py`, `test_field_contact_boundaries.py`, `test_monster_journeys.py`) | `state_to_dict(monster_activity.read_stored_monster_activity(wilderness))` |
| `from_stored` helper in `test_monster_activity.py` | return `activity_owner.read_stored_monster_activity(wilderness)` |
| `test_monster_journeys.py::test_missing_and_malformed_state_refuse_without_reset` | keep the test's intent with header shapes: save `header = dict(wilderness.db.monster_activity)`; for each of `{**header, "unknown": 1}`, `{**header, "settled_through_tick": True}`, `{**header, "units": header["units"] + ["t_no_such_unit"]}` assign it to `wilderness.db.monster_activity` and assert `MonsterActivityStateInvalid`; finally assign `header` back and assert the read equals the state read before |
| `test_regional_population.py::test_the_clock_contract_snapshots_the_population_surfaces` | the expected key set becomes the six non-activity keys united with `set(monster_activity.activity_record_surfaces(self.wilderness))` |
| `self.wilderness.db.monster_activity["settled_through_tick"] = 777` (`test_monster_activity.py`) | unchanged: it mutates the header in place, which replaces the header's stored value object |
| `wilderness.attributes.remove("monster_activity")` (`test_regional_population_recovery.py`) | unchanged |

## Risks / Trade-offs

- [A writer that mutates a stored entry in place would be missed by the identity and equality comparison] → Every record type is a frozen dataclass and every writer goes through `_copy_state`/`_replace_group`; task 2.3 greps for in-place mutation of `member_time` on a stored group.
- [Each stored write walks every entry once to find the changed ones] → Pointer comparisons over a few thousand entries; the encode, copy and pickle it replaces are orders of magnitude more work.
- [A whole-record snapshot now names one entry per unit of the index] → Its total size equals the former single entry. `population-snapshot-part-scoping` narrows it for scoped passes.
- [An attribute cache reset while parts are loaded costs one lookup per part on the next read] → It only happens after a rollback or in tests.
- [The stored format is incompatible] → Accepted by the request: the database is dropped.

## Migration Plan

None. Recreate the database after this change is deployed.
