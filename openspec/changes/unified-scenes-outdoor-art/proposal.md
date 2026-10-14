# Proposal

## Why

Three outdoor archetypes currently have no bundled official artwork. Deliver their finished illustrations independently of generator and operator availability.

## What Changes

- Deliver distinct finished WebP illustrations for wilderness_path, mountain_path, and coastal_path, with source/license and production records.
- Serve them as tracked static assets; do not add an incomplete scene registry or generation jobs.
- **BREAKING** establish the closed tracked-scene exception and current exclusion-test update before the first artwork bytes; later packs depend on this change.

## Capabilities

### New Capabilities

- `bundled-outdoor-scene-art`: Bundled outdoor scene art behavior defined in this change.

### Modified Capabilities

- `official-artwork-catalog`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-gallery-fallback`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

web/static/art/scenes/{wilderness_path,mountain_path,coastal_path}.webp; per-image provenance sidecars; world/art/tests/test_bundled_outdoor_art.py; web/tests/browser/test_browser_bundled_scene_assets.py; shard manifests.

## Effort and Boundary

Estimated **7.0 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: none

Code-conflict notes:
- Asset packs own disjoint images/sidecars/tests; shared .github/evennia-shards.json, .github/browser-shards.json and tools/test_data_freeze.json require serial manifest integration.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
