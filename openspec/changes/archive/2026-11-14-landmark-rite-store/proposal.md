# Proposal

## Why

The rite surfaces exist as components and the `rite` panel is published, but the browser has no state that says whether the rite card or the rite stage is open, whether a rite request is in flight, or which delivery is playing. The approved flow (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2) needs that state in one place before the shell can mount anything. This change adds it as a store group, tested without any component.

No player-visible change: nothing reads the group yet.

## What Changes

- New rite store group publishing `view.rite`: the committed panel, the local phase (closed, card, stage), whether the card is a revisit, the pending request and the delivery being played.
- The card opens when the panel becomes available for a new district during a session, never on a session's first snapshot.
- Approaching, leaving and reopening are local transitions that send nothing. Performing dispatches `explore.landmark_rite` exactly once and adopts its result.
- An open card or stage counts as a centred card: it stops walking and the compass, like the camp card.
- The group resets when the panel becomes unavailable, the mode leaves exploration or the session changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-landmark-rite`: the rite presentation state and its transitions.

## Impact

- New: `web/webclient-app/stores/elosern/rite.js`, `web/webclient-app/tests/rite/store.test.js`.
- Edits: `web/webclient-app/stores/elosern.js` (compose the group), `web/webclient-app/stores/elosern/view.js` (settle the group and publish `view.rite`).

## Batch:

- depends-on: landmark-rite-surfaces
- conflicts: `landmark-rite-stage`, `landmark-rite-performer-picking` and `landmark-rite-discovery-notice` edit `stores/elosern/rite.js`; they run after this change and serially.
