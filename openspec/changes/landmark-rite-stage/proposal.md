# Proposal

## Why

The `rite` panel is published and the rite surfaces exist as tested components, but nothing mounts them. A browser player on a district landmark still sees only the generic landmark card and cannot perform a rite without typing the text command. This change wires the approved flow of the design's §12.2 into the live client: arrival card, 走近, the AVG rite stage with the party standing on it, the rite panel, scene playback through the shared authored-scene player, and the return entry.

## What Changes

- A shell composable binds the rite store group (`landmark-rite-store`) to the client shell.
- On a committed arrival at a rite landmark the rite arrival card opens in the choices anchor instead of the generic landmark card, in the wilderness and in a settlement room alike. 退開 and 走近 are local and send nothing.
- 走近 presents the stage as the dialogue stage does: the message region spans the band, the cockpit anchors recede, the party stands in the left actor anchor, the rite backdrop replaces the map, and the message window shows the guardian's form under the guardian's name plate.
- Picking an option dispatches `explore.landmark_rite` once with the controlled character as performer. On success the delivered scene plays through the existing `use-authored-scene.js` and `MessageWindow`; when it finishes the panel returns.
- While the `rite` panel is available and neither the card nor the stage is open, a return entry `◆ <guardian> 儀式` (key R) under the place card reopens the card.
- Leaving the landmark, or the server leaving exploration mode, closes the card and the stage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-landmark-rite`: the live flow from arrival to playback and return.
- `authored-scene-playback`: the shared player also renders rite deliveries.

## Impact

- New: `web/webclient-app/composables/use-rite-stage.js`, `web/webclient-app/components/rite/RiteEntry.vue`, `web/webclient-app/tests/app_client_rite.test.js`.
- Edits: `web/webclient-app/AppClient.vue`, `web/webclient-app/composables/use-window-hotkeys.js`, `web/webclient-app/stories/World/LandmarkRite.stories.js` (an entry story), `web/webclient-app/AGENTS.md`.
- The performer is always the controlled character in this change (`landmark-rite-performer-picking`). No line announces a newly lit district (`landmark-rite-discovery-notice`).

## Batch:

- depends-on: landmark-rite-store
- conflicts: `landmark-rite-performer-picking` and `landmark-rite-discovery-notice` edit `AppClient.vue` or `use-rite-stage.js`; they run after this change and serially. The managed browser journeys are `landmark-rite-journeys`.
