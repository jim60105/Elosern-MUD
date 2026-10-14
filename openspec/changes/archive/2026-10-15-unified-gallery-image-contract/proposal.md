# Proposal

## Why

Gallery previews have independent loading paths and exact requested images need attributed failures without changing job truth.

## What Changes

- Integrate backend canonical descriptors and the already production-used shared lifecycle through every gallery preview, with source-attributed failures independent of job truth.
- **BREAKING** replace gallery card/official row image fields with artwork descriptors at gallery schema version 3; update every serializer, active validator and gallery consumer together.
- Migrate all gallery previews to shared load results and persistent accessible local errors; editors read exact original descriptors in this wire cutover and keep their existing local editing lifecycle until the explicit editor change.

## Capabilities

### New Capabilities

- `artwork-descriptor`: Artwork descriptor behavior defined in this change.

### Modified Capabilities

- `webclient-gallery-panel`: Amend the owned artwork contract while retaining unrelated scenarios.
- `webclient-gallery-ui`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-gallery-resolution`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/descriptors.py; web/webclient/presentation/gallery.py; protocol/panels/gallery.js and version tables; Vue gallery components/store/stories; lib/image-attempts.js, composables/useArtwork.js, components/ArtworkFailure.vue and ArtworkPreview.vue.

## Effort and Boundary

Estimated **6.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-art-source-faults
depends-on: unified-image-loading-core

Code-conflict notes:
- Conflicts with original-editors in all Gallery*.vue, gallery tests and stories; with portrait integration in descriptor/load modules and protocol envelope constants; with scene integration in shared loading additions.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
