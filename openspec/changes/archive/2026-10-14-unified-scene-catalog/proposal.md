# Proposal

## Why

The current catalog supports only external portrait content, and media serving has no closed bundled-scene namespace.

## What Changes

- Add immutable art-domain scene definitions for all ten registered archetypes plus dream_throne, with declared terminal keys.
- Admit and serve all eleven completed lawful images from four prerequisite artwork packs with separate trusted roots and fingerprints.

## Capabilities

### New Capabilities

- `bundled-scene-art`: Bundled scene art behavior defined in this change.

### Modified Capabilities

- `official-artwork-catalog`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/{scene_definitions.py,official.py,service.py,no_follow.py}; web/art_media.py; world/art/tests/test_bundled_scenes.py; web/webclient/tests/test_art_media.py; docs/development/official-artwork-deployment.md; static scene collection.

## Effort and Boundary

Estimated **7.25 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scenes-outdoor-art
depends-on: unified-scenes-interior-art
depends-on: unified-scenes-sacred-art
depends-on: unified-scenes-terminal-art

Code-conflict notes:
- Conflicts with unified-art-source-faults in official.py/service.py and catalog spec; with unified-room-art-metadata in authored key registry; with scene cutover in media tests/docs.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
