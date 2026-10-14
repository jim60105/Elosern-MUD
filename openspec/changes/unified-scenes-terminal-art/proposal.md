# Proposal

## Why

Town and forest terminal images need known redistribution rights without making catalog scope depend on unverified sample licensing.

## What Changes

- Deliver two complete original or verified-lawful forest_path and city_street WebPs plus provenance as a separately budgeted artwork slice.
- Do not assume sample generation metadata proves distribution rights; real production is included in the estimate.

## Capabilities

### New Capabilities

- `bundled-terminal-scene-art`: Bundled terminal scene art behavior defined in this change.

### Modified Capabilities

None.

## Impact

web/static/art/scenes/{forest_path,city_street}.webp and per-image provenance; world/art/tests/test_bundled_terminal_art.py; common asset-browser test and shard/data ledgers.

## Effort and Boundary

Estimated **4.75 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-scenes-outdoor-art

Code-conflict notes:
- Disjoint two-image production; serialize common browser/data/shard manifests with other artwork packs.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
