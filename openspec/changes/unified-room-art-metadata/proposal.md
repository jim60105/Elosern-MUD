# Proposal

## Why

Permanent interiors currently use plain Room without scene metadata, and pooled wilderness assigns region keys that are not scene archetypes.

## What Changes

- Apply source-authored stable room_art_key and valid scene metadata through map/bootstrap/instance owners, including permanent interiors.
- Use logical coordinate identity for pooled wilderness, reset old art keys on each prepare, and map region definitions to registered scene types.
- Expose a read-only bounded logical scene identity without using pooled ObjectDB id, translated names or inferred artwork keys; no new room generation.

## Capabilities

### New Capabilities

- `room-art-metadata`: Room art metadata behavior defined in this change.

### Modified Capabilities

None.

## Impact

world/maps/{bootstrap.py,wilderness_provider.py,instance.py,map_data.py}; typeclasses/rooms.py; authored settlement/place/wilderness records; world/art/scene_definitions.py authored room-key registry; map/typeclass tests.

## Effort and Boundary

Estimated **6.25 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scene-catalog

Code-conflict notes:
- Conflicts with scene-catalog in registered authored room keys; with scene-rendering in art_view.py if scene-view input is touched; freeze map/schema owner until metadata integration lands.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
