# Proposal

## Why

The tavern, dungeon, and ruin must remain visually identifiable with external artwork unavailable.

## What Changes

- Deliver distinct finished tavern_interior, dungeon_interior, and ruin_interior WebP landscapes.
- Record lawful distribution terms, production provenance, resource-limit tests and real static serving smoke.

## Capabilities

### New Capabilities

- `bundled-interior-scene-art`: Bundled interior scene art behavior defined in this change.

### Modified Capabilities

None.

## Impact

web/static/art/scenes/{tavern_interior,dungeon_interior,ruin_interior}.webp and provenance sidecars; world/art/tests/test_bundled_interior_art.py; existing asset-browser module and shard/data manifests.

## Effort and Boundary

Estimated **6.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scenes-outdoor-art

Code-conflict notes:
- Disjoint asset/test paths from other packs; serialize edits to the common asset-browser module and shard/data manifests.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
