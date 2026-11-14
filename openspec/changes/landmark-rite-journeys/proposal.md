# Proposal

## Why

The rite flow is mounted in the client shell and covered by component and app-level tests in a simulated DOM. Layout, focus and overflow in a real browser at the two supported viewports are not covered, and the flow crosses the travel layout, the dialogue presentation and the shared scene player. This change adds the managed browser journeys the design's §15 names: one from a wilderness arrival and one from the city landmark's room.

## What Changes

- Two managed browser journeys drive arrival, approach, option, scene pages and leave with synthetic committed data, and check the stage at 1451x790 and 2560x1440.
- Defects the journeys expose in the rite components or the shell bindings are fixed here.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-landmark-rite`: the flow is verified in the live client at two viewports.

## Impact

- New: `web/tests/browser/test_landmark_rite.py`.
- Edits: `.github/browser-shards.json`; rite components or `AppClient.vue` bindings only where a journey exposes a defect.

## Batch:

- depends-on: landmark-rite-stage
- conflicts: edits rite components only for defects; run serially with `landmark-rite-performer-picking`.
- parallel with: `landmark-rite-lighting`.
