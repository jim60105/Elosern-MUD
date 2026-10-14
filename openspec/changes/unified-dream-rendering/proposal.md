# Proposal

## Why

Dream artwork is currently a raw optional URL with its own load handling, so it cannot use the scene contract or required offline dream art.

## What Changes

- **BREAKING** replace dream state scene_art URL with canonical scene descriptor at dream schema version 3, updating narrative read model, presenter, validators and DreamPanel together.
- Preserve npc/dream_goddess/dream-throne.webp as optional preferred source, then bundled dream_throne and distinct town terminal.
- Reuse the scene renderer/loading/failure state and full-view semantics without dream generation, physical background inheritance or lifecycle changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-dream-stage`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/narrative/dream_surface.py; world/art/presenter.py; web/webclient/presentation/dream.py; protocol/panels/dream.js/version tables; DreamPanel.vue; dream unit/component/browser tests and docs.

## Effort and Boundary

Estimated **4.75 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scene-rendering

Code-conflict notes:
- Conflicts with scene-rendering in shared scene renderer/presenter; with avatar/editor story manifests; no mutation of dream_session/authoring/dialogue dispatch.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
