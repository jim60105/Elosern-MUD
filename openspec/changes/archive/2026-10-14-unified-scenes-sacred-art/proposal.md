# Proposal

## Why

Cave, shrine, and dream scenes need their own real artwork rather than town or forest substitutions.

## What Changes

- Deliver distinct cave_interior, shrine_interior, and dream_throne WebP landscapes.
- Include source/license and production records, decode checks and static-browser smoke; no dream lifecycle or protocol change.

## Capabilities

### New Capabilities

- `bundled-sacred-scene-art`: Bundled sacred scene art behavior defined in this change.

### Modified Capabilities

None.

## Impact

web/static/art/scenes/{cave_interior,shrine_interior,dream_throne}.webp and provenance sidecars; world/art/tests/test_bundled_sacred_art.py; existing asset-browser module and shard/data manifests.

## Effort and Boundary

Estimated **6.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scenes-outdoor-art

Code-conflict notes:
- Disjoint asset/test paths; common asset-browser module, shard and data manifests require serialized integration.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
