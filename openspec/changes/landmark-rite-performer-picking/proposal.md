# Proposal

## Why

The settlement, the action and the `rite` panel already support a companion performing a rite, but the browser always sends the controlled character. The approved interface (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2) picks the performer on the stage the way a combat target is picked: the party figures are the hit areas, the picked figure is lit and the others dim, and ArrowLeft and ArrowRight step through the performers from the panel.

Shipped options declare no watch scene until `landmark-rite-watch-perspectives`, so picking stays unreachable in the live game until then. This change is the mechanism; it is tested with synthetic panels.

## What Changes

- The rite store group holds the picked performer. It resets to the controlled character on every entry to the stage and when the picked performer leaves the panel's `performers`.
- Picking is offered only when the panel lists more than one performer and at least one option admits a companion.
- While picking is offered, the party line-up's figures of the listed performers are hit areas through the line-up's existing targeting input: the picked figure is lit and selected, a hovered figure is lit, and the others dim. During playback the performer's figure stays lit and nothing is selectable.
- The rite panel shows a switching hint and steps the performer with ArrowLeft and ArrowRight.
- The dispatched action carries the picked performer's `member_id`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-landmark-rite`: performer picking on the stage and from the panel.

## Impact

- Edits: `web/webclient-app/stores/elosern/rite.js`, `web/webclient-app/composables/use-rite-stage.js`, `web/webclient-app/components/rite/RitePanel.vue`, `web/webclient-app/AppClient.vue` (the line-up's `targeting` and `target-pointer` bindings), `web/webclient-app/stories/World/LandmarkRite.stories.js`, `web/webclient-app/tests/rite/store.test.js`, `web/webclient-app/tests/rite/surfaces.test.js`, `web/webclient-app/tests/app_client_rite.test.js`, `web/webclient-app/AGENTS.md`.
- No server change. `CompanionLineup.vue` is not edited.

## Batch:

- depends-on: landmark-rite-stage
- conflicts: `landmark-rite-discovery-notice` edits `stores/elosern/rite.js` and `use-rite-stage.js`, and `landmark-rite-journeys` may fix rite components; run serially with them.
