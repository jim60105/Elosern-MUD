# Proposal

## Why

Portrait attempt enumeration and attributed backend faults are a separate art-domain integration from the atomic browser wire cutover.

## What Changes

- Introduce the canonical portrait attempt enumerator preserving existing equipment/selection/default/classic/official order and age/species/alpha rules.
- Use it inside existing read-only portrait resolution and facade diagnostics immediately while retaining the current registered single flat presentation contract until its owning atomic cutover.
- Keep resolve_scene/resolve_subject scene behavior unchanged; no dual-wire or old-path alias is introduced.

## Capabilities

### New Capabilities

- `portrait-source-attempts`: Portrait source attempts behavior defined in this change.

### Modified Capabilities

- `official-art-resolution`: Amend the owned artwork contract while retaining unrelated scenarios.
- `official-art-personalization`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-gallery-fallback`: Amend the owned artwork contract while retaining unrelated scenarios.
- `art-gallery-resolution`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

world/art/presenter.py; gallery_match.py/gallery_fallback.py; world/art/tests/test_portrait_attempts.py and affected existing direct presenter tests; art developer docs.

## Effort and Boundary

Estimated **6.5 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-gallery-image-contract

Code-conflict notes:
- Conflicts with portrait wire change in resolver/tests; old scene delegation must remain unaffected until scene owner.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
