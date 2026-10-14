# Proposal

## Why

Original-image editors currently track dimensions and load success independently. A substituted preview must never become saveable geometry.

## What Changes

- Replace both original editor load paths with shared exact-original results; loading and failed-original explanations stay distinct.
- Gate face/stage saves on decoded exact identity and usable dimensions; reset on source change and ignore stale callbacks.
- Observe the fixed adult-size ruler separately, show its resource failure, and prevent any ruler/substitute save.

## Capabilities

### New Capabilities

- `original-image-edit-eligibility`: Original image edit eligibility behavior defined in this change.

### Modified Capabilities

- `webclient-gallery-ui`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

GalleryFaceRectModal.vue; GalleryStageTransformModal.vue; face-rect-edit.js; stage-transform-edit.js; gallery component tests/stories and focused new browser tests.

## Effort and Boundary

Estimated **5.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-image-loading-core
depends-on: unified-gallery-image-contract

Code-conflict notes:
- Serialize Gallery*.vue and gallery story/test/evidence manifests with image-contract; no wire version change and no scene/portrait selector edits.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
