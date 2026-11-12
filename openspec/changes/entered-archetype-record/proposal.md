# Proposal: the entered-archetype record

## Batch:

Gallery window programme, stage 3 ("The category": "Lists the archetypes the
live character has entered. The fact is recorded at the existing room-entry
seam that ensures the scene asset, per character.").

- depends-on: none (deterministic-core module plus two hook lines; delivery
  order places it in stage 3)
- conflict: `typeclasses/rooms.py` (`GridRoom.at_object_receive`,
  `InstanceRoom.at_object_receive`); no other programme change edits them.

## Why

The 背景 category lists only archetypes the character has entered. That fact
is not stored anywhere; it must be written by one deterministic module at the
seam that already ensures the scene asset.

## What Changes

- New `world/rules/scene_visits.py`: `record_scene_entry(character,
  archetype)` (never raises) and `entered_archetypes(character)` (read-only,
  registry order, registered only), storing a per-character attribute.
- `GridRoom.at_object_receive` and `InstanceRoom.at_object_receive` call
  `record_scene_entry(obj, self.scene_archetype)` beside
  `ensure_scene_asset`, for the same `PlayerCharacter` arrivals.

## Capabilities

### New Capabilities

- `scene-entry-record`: the per-character record of entered scene archetypes.

### Modified Capabilities

None.

## Impact

- New: `world/rules/scene_visits.py`, `world/rules/tests/test_scene_visits.py`
  (shard entry). Edited: `typeclasses/rooms.py`.
- Estimate: 4 hours (module 1 h, hooks 0.5 h, tests 2 h, gates 0.5 h).
