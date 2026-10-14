# Proposal

## Why

One shared resource lifecycle needs a real first integration before atomic gallery/portrait/scene wire changes, keeping each cutover below one day.

## What Changes

- Introduce and production-integrate the ordered load/decode/fault reducer and local resource driver through the existing face-rectangle editor.
- Keep the existing gallery v2 wire unchanged; the editor passes one exact committed original resource request, without manufacturing subject resolution or accepting multiple wire shapes.
- Add shared accessible local failure/alpha drawing primitives and tested provisional resource semantics for dependent renderers.

## Capabilities

### New Capabilities

- `image-attempt-lifecycle`: Image attempt lifecycle behavior defined in this change.

### Modified Capabilities

- `webclient-gallery-ui`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

lib/image-attempts.js; composables/useImageAttempts.js; ArtworkFailure.vue and ArtworkAlpha.vue; GalleryFaceRectModal.vue; focused core/editor tests, test-only image fixture and docs.

## Effort and Boundary

Estimated **7.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: none

Code-conflict notes:
- Conflicts with gallery contract and original editors in face editor/loader/tests; test fixture/manifest edits serialize.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
