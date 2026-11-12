# Design: the entered-archetype record

## Context

- `typeclasses/rooms.py`: `GridRoom.at_object_receive` and
  `InstanceRoom.at_object_receive` call
  `world.art.service.ensure_scene_asset(self.scene_archetype)` when `obj` is a
  `PlayerCharacter`. `TerrainRoom` (wilderness) defines no such hook: the
  wilderness contrib assigns `.location` directly, so no wilderness entry
  reaches this seam (verified; noted under Risks).
- `world.lore.scene_archetypes.SCENE_ARCHETYPE_REGISTRY` is the registry.
- Precedent for a tolerant per-character record:
  `world/rules/map_knowledge.record_arrival`.

## Goals / Non-Goals

**Goals:** writer, reader, two hook calls.

**Non-Goals:** listing (`gallery-scene-category`); wilderness entry (no seam
exists; adding one is outside the design).

## Decisions

### D1. Storage and API (verbatim)

Attribute `entered_scene_archetypes` on the character:
`{"schema_version": 1, "archetypes": [<archetype key>, ...]}` (sorted unique
list).

```python
def record_scene_entry(character, archetype) -> None   # never raises
def entered_archetypes(character) -> tuple[str, ...]  # registry order; never writes
```

- `record_scene_entry`: no-op unless `character` is a `PlayerCharacter` and
  `archetype in SCENE_ARCHETYPE_REGISTRY`; a corrupt stored value logs
  `scene_entry_record_corrupt` and returns; an archetype already present
  writes nothing; otherwise insert, re-sort, save and emit
  `scene_entry_recorded` (info, `char`, `archetype`). Exceptions →
  `log_warn("scene_entry_record_failed", exc=...)`.
- `entered_archetypes`: tolerant read; return
  `tuple(k for k in SCENE_ARCHETYPE_REGISTRY if k in stored)`.

### D2. Ordering (planner decision)

The design does not order scene subjects; registry order keeps tiles stable as
the player travels, unlike people, whose design orders by recency.

### D3. Hooks

In both hooks, after `ensure_scene_asset(self.scene_archetype)`:
`from world.rules.scene_visits import record_scene_entry;
record_scene_entry(obj, self.scene_archetype)`.

## Risks / Trade-offs

- [Wilderness archetypes are never recorded because wilderness entry has no
  scene-ensure seam] → they are not listed under 背景; flagged in the
  programme report for the user.
- [Entries made while possessing a companion] → the seam fires only for
  `PlayerCharacter` arrivals, exactly as the scene ensure does; a possessed
  companion's entry records nothing (planner decision, flagged).
