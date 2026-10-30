# Proposal

## Why

Select the wilderness presentation, remap HUD slots, refresh the live area map and show committed party medallions without waiting for sight rules. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Select the wilderness presentation, remap HUD slots, refresh the live area map and show committed party medallions without waiting for sight rules.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-layout`: Select the wilderness presentation, remap HUD slots, refresh the live area map and show committed party medallions without waiting for sight rules.

### Modified Capabilities
- `webclient-map-drawer`: Amend existing exact contracts for this travel slice.
- `webclient-contextual-hud`: Amend existing exact contracts for this travel slice.
- `webclient-status-presentation`: Amend existing exact contracts for this travel slice.

## Impact

Existing owners are AppClient.vue (slot composition), components/HudFrame.vue (anchor geometry), composables/use-map-drawer.js (on-demand maps), stores/elosern/view.js (committed projection), stores/elosern.js (public facade), components/CompanionLineup.vue and AvatarArtwork.vue (identity/art projection). All frontend paths below are relative to web/webclient-app/. Server status.py currently emits schema4 fatigue rows; world/rules/status_query/fatigue.py reads exact physiology without materializing it. Logical wilderness identity is already art.scene.artwork.subject_id, produced by world/maps/room_art.py::wilderness_scene_identity; there is no separate room panel.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:


Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
