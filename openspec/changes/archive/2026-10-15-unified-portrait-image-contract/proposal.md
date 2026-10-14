# Proposal

## Why

Portrait surfaces copy incomplete fields and drop references for missing real images, so correct silhouettes and source faults do not reach every figure.

## What Changes

- Use the production-integrated canonical portrait enumerator from unified-portrait-source-resolution; this slice owns complete admitted descriptors, atomic wire migration and figures rather than new backend source selection.
- **BREAKING** cut over art portrait catalog and account roster to complete descriptors, increment art 2→3 and roster current→next versions, and migrate all portrait consumers and active validators in this change.
- Render all figures through ReferenceArtwork/shared loading in both layout modes; retain truthful generation, per-source geometry, alpha failure handling and local fault visibility.
- Avatar callsites read the new descriptor directly with their existing rendering policy here; their shared renderer and grapheme policy are owned by unified-avatar-rendering.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-art-panel`: Amend the owned artwork contract while retaining unrelated scenarios.
- `webclient-character-roster`: Amend the owned artwork contract while retaining unrelated scenarios.
- `webclient-party-panel`: Amend the owned artwork contract while retaining unrelated scenarios.
- `webclient-exploration-menu`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-gallery-resolution`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/{presenter.py,gallery_match.py,gallery_fallback.py}; world/rules/art_view.py; web/webclient/presentation/{art.py,roster.py,party.py,exploration.py}; active protocol art/misc validators/version tables; ReferenceArtwork.vue, StageActor.vue, AppClient.vue, all avatar readers, party helpers.

## Effort and Boundary

Estimated **7.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-portrait-source-resolution

Code-conflict notes:
- Conflicts with avatar-rendering in avatar readers; with scene-rendering in art.py, art_view.py, art validators/version/stories; serialize shared descriptor/failure components with gallery.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
