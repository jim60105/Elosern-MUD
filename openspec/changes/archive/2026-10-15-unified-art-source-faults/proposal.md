# Proposal

## Why

An empty catalog currently erases unavailable-root and source-specific rejection facts, making a broken configured source indistinguishable from optional absence.

## What Changes

- Retain bounded root/configuration, requested-default, rejection and selected-source metadata facts in startup snapshots.
- Keep invalid default faults before deterministic substitutes and isolate unselected sibling rejection diagnostics.
- **BREAKING** distinguish optional default-root absence from configured/unreadable roots in existing catalog requirements; preserve read-only restart semantics.

## Capabilities

### New Capabilities

- `art-source-fault-facts`: Art source fault facts behavior defined in this change.

### Modified Capabilities

- `official-artwork-catalog`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/official.py; server/conf/settings.py configuration provenance without new settings; world/art/tests/test_official_catalog.py; docs/development/official-artwork-deployment.md.

## Effort and Boundary

Estimated **5.75 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scene-catalog

Code-conflict notes:
- Serialize official.py, settings provenance, catalog delta and deployment guide with scene-catalog; downstream descriptors consume this snapshot without rescanning.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
