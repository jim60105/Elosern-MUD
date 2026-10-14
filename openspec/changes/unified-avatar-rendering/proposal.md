# Proposal

## Why

Small portraits use several local failed-URL caches and code-point initials. Every avatar needs one policy with grapheme-safe text and persistent accessible failure information.

## What Changes

- Integrate one AvatarArtwork renderer for roster/switcher, presence, party and combat participants plus any existing dialogue avatar reader.
- Use successful image face geometry or first Unicode grapheme of trimmed name, neutral text for empty name, and never request silhouette images.
- Remove avatar-local source selection/caches and share the common failure mapping and keyboard-accessible marker.

## Capabilities

### New Capabilities

- `avatar-artwork-presentation`: Avatar artwork presentation behavior defined in this change.

### Modified Capabilities

- `webclient-art-panel`: Amend the owned artwork contract while retaining unrelated scenarios.

## Impact

AvatarArtwork.vue; character-identity.js; CharacterSwitcher.vue; PresenceRail.vue; PartyDrawer.vue; ParticipantFrame.vue; any remaining real avatar consumers; stories/component-manifest and focused tests.

## Effort and Boundary

Estimated **5.25 engineer-hours**, including owned artwork production, implementation, focused tests, concrete fixture/smoke work, documentation and gates. tasks.md itemizes the complete strictly sub-eight-hour slice. No placeholder/scaffold-only deliverable, compatibility shim, migration or unestimated catch-up work is permitted. No gameplay, generation scheduling, commands, GM previews, telemetry ingestion, retry service or operator hot reload changes.

## Batch:

depends-on: unified-portrait-image-contract

Code-conflict notes:
- Conflicts with portrait-contract in these avatar readers and art spec; shared component manifest/shard files serialize with editors/dream.

Shared interfaces, complete approved-design ownership and the fifteen-change dependency/conflict matrix are in `../unified-gallery-image-contract/design.md`. Authority is the approved unified-image design and amended engine D10/section 8. These are planning artifacts only; apply requires separate authorization.
