# Proposal

## Why

The monster-activity state of the whole world (every group, journey and receipt) is one Evennia attribute, `wilderness.db.monster_activity`. Every stored write encodes, deep-copies and pickles the whole record (`world/maps/monster_activity.py::_write_state`), and the next read decodes and cross-checks the whole record again, because the stored value object changed. A settlement that changed three groups of one settlement unit pays for all 2,490 groups of the world. The same cost is paid by every single-group write outside a settlement pass (a combat round, a departure, a registration).

A cProfile of one background drain run on a copy of the live database, after commit `c0736d44`, attributes about 0.22 s of a 0.42 s run to these whole-record writes.

## What Changes

- **BREAKING (stored format)**: the activity record is stored as one small header attribute plus one stored part per settlement unit. A part holds the groups whose home lies in that unit, with their journeys and receipts. There is no compatibility path and no migration: the database is dropped.
- A write stores only the parts whose entries changed, plus the header. A part that did not change is not encoded, pickled or saved.
- A read assembles the same immutable `MonsterActivityState` as before. An unchanged part is not decoded again after another part was written.
- A rollback snapshot of the activity record covers the header and every part, including a part a failed operation created, so a failed write leaves no part behind in memory or in the database. (Narrowing that snapshot to the parts of one scope is the next change, `population-snapshot-part-scoping`.)
- New public functions for tools and tests: `write_monster_activity`, `read_stored_monster_activity`, `activity_record_surfaces`, `part_key`.
- The in-memory API (`read_monster_activity`, `MonsterActivityState`, every owner operation, `state_to_dict`, `state_from_dict`, `batched_state_writes`) keeps its signatures and meaning. No settlement outcome changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: the activity record is stored per settlement unit and a write stores only the parts it changed.

## Impact

- Code: `world/maps/monster_activity.py` (storage section, snapshot helper), `world/maps/regional_population.py` (`snapshot_population_surfaces`).
- Tests: new `world/maps/tests/test_monster_activity_parts.py` (registered in `.github/evennia-shards.json`); edits to the test modules that write or read `wilderness.db.monster_activity` directly (listed in `design.md` D8).
- Documentation: `docs/development/regional-monster-population.md` (new section "Activity record storage"), `docs/development/monster-field-behaviour.md` (one sentence naming the stored form).
- Stored data: the wilderness script gains one attribute per settlement unit that ever held a group (category `monster_activity_part`). An existing database cannot be read; it must be recreated.
- Human-reviewed: none. Every behaviour of this change is established by tests. The profile numbers above are context, not acceptance criteria.

## Batch:

- depends-on: none
- This change does not require commit `c0736d44` (`fix/population-group-units-memo`); it touches no file of that commit.
- conflicts: `population-snapshot-part-scoping` edits the same snapshot functions and is ordered after this change. `population-drain-batched-runs` relies on the read identity rule of design D3 and is ordered after both.
- parallel with: `population-drain-idle-gate` (no shared file).
