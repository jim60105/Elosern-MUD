# Proposal

## Why

The owner wants each subrace to start in its own settlement's gathering room instead of
虛境. Before activation can move a character there, the game needs a validated
declaration of which settlement each subrace starts in, and a way to turn that
declaration into a room. This change adds both and does not yet change behavior.
`subrace-start-settlements` then uses them in activation.

## What Changes

- New lore registry `world/lore/start_locations.py`. It maps every subrace key to
  exactly one start settlement, named by its anchor (location) identity. Import fails if
  a subrace has no row, a row names an unknown subrace, or a row is malformed. It is
  listed in the registry inventory (`world/lore/registry_index.py`).
- The static-reference closure (`world/maps/static_references.py`) gets a
  start-location family. Map-world adoption is rejected when a start anchor has no
  settlement placement in the candidate world. The start room is always that
  settlement's anchor room. It is found through the anchor placement, never through a
  coordinate or a dbref.
- New rules module `world/rules/start_location.py` (`resolve_start_room`,
  `StartLocationError`). It resolves a subrace's start room from the current settlement
  graph and the materialized grid room, with no fallback.
- The synthetic data kit gets one start-location row and a documented coupling with
  its anchor-placement swap.
- The shipped mapping (15 rows) is game data. It is listed in design D5, not in the spec.

## Batch:

- depends-on: elven-villages-eolas-fionnen (merged to master as e076e764; two rows need
  its `elven_village_eolas` and `elven_village_fionnen` documents)
- Batch order: `subrace-start-locations` (this change), `subrace-start-settlements`,
  `entrance-probe-fixtures`, `retire-limbo-city-gates`, `drop-settlement-city-gate-field`.
- Conflict notes: `retire-limbo-city-gates` also edits `world/maps/static_references.py`
  and `world/maps/tests/test_static_map_references.py`. Apply this change first.

## Capabilities

### New Capabilities

- `character-start-location`: the per-subrace start-settlement registry, its
  validation at import and at map-world adoption, and resolving it to a room.

### Modified Capabilities

None.

## Impact

- Code: `world/lore/start_locations.py` (new), `world/lore/registry_index.py`,
  `world/rules/start_location.py` (new), `world/maps/static_references.py`,
  `world/rules/AGENTS.md`.
- Tests: new `world/lore/tests/test_start_locations.py` and
  `world/rules/tests/test_start_location.py`; additions to
  `world/maps/tests/test_static_map_references.py`; the synthetic kit
  (`data_characters.py`, `targets.py`, `__init__.py`).
- No human-reviewed document. Every requirement is mechanism-testable.
