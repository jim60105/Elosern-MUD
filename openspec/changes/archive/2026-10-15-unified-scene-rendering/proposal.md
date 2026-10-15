# Proposal

## Why

Scene backgrounds currently select mode-dependent samples and retain previous-place images. Ordinary scenes need complete room-aware precedence and same-place-only retention.

## What Changes

- **BREAKING** replace art.scene image fields with canonical descriptor at art schema version 4 and migrate serializer, active validators, store and SceneBackdrop/fullview atomically.
- Implement room official > generated archetype > optional operator type > required bundled type > distinct declared terminal > non-image background.
- Add same-scene regeneration retention separate from current attempts, latent provisional results, stale callback protection, persistent source failures and no previous-place retention.
- Remove obsolete sample CSS, town/forest sample copies and scene failure caches; keep unrelated sample-guild artwork and unrelated protocol code.

## Capabilities

### New Capabilities

- `scene-artwork-presentation`: Scene artwork presentation behavior defined in this change.

### Modified Capabilities

- `webclient-art-panel`: Amend the owned artwork contract while retaining unrelated scenarios.
- `webclient-contextual-hud`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-queue-worker`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/presenter.py; world/rules/art_view.py; web/webclient/presentation/art.py and art_push.py; art validators/version tables; SceneBackdrop.vue; AppClient.vue; lib/image-attempts.js; app-shell.css; scene tests/browser/stories.

## Effort and Boundary

Estimated **7.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-portrait-image-contract
depends-on: unified-room-art-metadata

Code-conflict notes:
- Serialize art.py, art_view.py, art schema/stories and shared loader with portrait-contract; shared CSS and component manifest with avatar/dream; no gallery mutation files.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
