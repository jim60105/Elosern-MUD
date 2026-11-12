# Proposal: the met-person record

## Batch:

Gallery window programme, stage 2 ("Specification 2: people", section "The
met-person record", of `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: none (pure deterministic-core module; delivery order places it
  after `gallery-window-mount`)
- conflict: none; new module, new test module, one shard entry.

## Why

The 人物 category lists named NPCs the live character has interacted with,
grouped by place. That fact does not exist yet. It must be owned by the
character, written by exactly one module outside the read-only presenter, and
tolerant of NPCs that no longer exist.

## What Changes

- New deterministic-core module `world/rules/met_people.py`, the single
  writer and reader of a per-character record keyed by the NPC's portrait
  stable key, holding the NPC identity, the place and the time of the last
  interaction.
- Place derivation: the settlement the room belongs to, else the wilderness
  region of the cell; an instance room resolves through its origin room;
  districts are never used.
- Possession: an interaction made through a possessed companion is recorded
  for the character that owns it.
- Reads skip vanished NPCs; the writer drops them on its next write.
- No call site yet (`met-person-write-points`).

## Capabilities

### New Capabilities

- `met-person-record`: the per-character record of named NPCs met, with
  place and time.

### Modified Capabilities

None.

## Impact

- New: `world/rules/met_people.py`, `world/rules/tests/test_met_people.py`,
  one entry in `.github/evennia-shards.json`.
- Reads: `world/art/subjects.character_subject_for`,
  `world/rules/party.bound_owner_of`, `world/rules/clock.read_world_clock`,
  `world/maps/map_data.SETTLEMENT_GRAPHS`,
  `world/maps/wilderness_provider.region_for_coordinates`,
  `world/lore/wilderness_regions.regions`, `world/lore/anchors`,
  `world/lore/wilderness_entry.WILDERNESS_ENTRY_REGISTRY`.
- Estimate: 5 hours (module 2 h, place derivation 1 h, tests with the
  synthetic grid map and a synthetic wilderness cell 1.5 h, gates 0.5 h).
