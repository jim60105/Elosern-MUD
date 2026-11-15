# Proposal

## Why

After `landmark-rite-lighting`, the first completed rite at a landmark lights its district, but nothing tells the player so except the world map's own animation, which they see only if the map is open. The old movement narrative `已探明：<district>` is gone. This change restores the notice at the moment the district is actually earned: on the first completed rite, in the text client and on the rite stage (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2 "Playback and return").

## What Changes

- The rite completion message gains one line naming the newly explored district on the first completion at that district, and the server logs one discovery event. A repeated rite adds neither.
- The rite stage's message window shows one line naming the newly lit district after the first completion's scene finishes, until the player leaves the stage or performs again.
- The command reference states that the first rite at a landmark explores its district.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-district-discovery`: the first completed rite adds one discovery narrative.
- `webclient-landmark-rite`: the stage names a newly lit district.

## Impact

- Edits: `web/webclient/actions/rite_actions.py` (`rite_completion_line`), `world/rules/landmark_rites.py` (the commit callback), `web/webclient-app/stores/elosern/rite.js`, `web/webclient-app/composables/use-rite-stage.js`, their tests, `docs/game/command-reference.md`, `docs/development/map-panel-protocol.md`.

## Batch:

- depends-on: landmark-rite-lighting
- conflicts: `landmark-rite-performer-picking` edits `stores/elosern/rite.js` and `use-rite-stage.js`; run serially with it.
- parallel with: `landmark-rite-arrival-signal-removal`, `landmark-rite-art`.
